import { describe, expect, it } from "bun:test";
import { JSONParse } from "./JSONParse";

describe("JSONParse - native parity", () => {
  it("parses primitives the same way as JSON.parse", () => {
    expect(JSONParse("true")).toBe(true);
    expect(JSONParse("null")).toBe(null);
    expect(JSONParse('"hello"')).toBe("hello");
    expect(JSONParse("3.14")).toBe(3.14);
  });

  it("parses plain objects and arrays without altering shape", () => {
    const input = '{"name":"Alice","age":30,"tags":["a","b"],"active":true,"meta":null}';
    expect(JSONParse(input)).toEqual({
      name: "Alice",
      age: 30,
      tags: ["a", "b"],
      active: true,
      meta: null,
    });
  });

  it("leaves safe integers (<=16 digits, within MAX_SAFE_INTEGER) untouched", () => {
    expect(JSONParse('{"id": 1234567890123456}')).toEqual({ id: 1234567890123456 });
  });
});

describe("JSONParse - legacy custom-format BigInt strings", () => {
  // The reviver independently restores any string of the form -?\d+n back
  // to BigInt, regardless of whether the regex pass touched it. This is how
  // the lib stays compatible with JSON produced by older versions, which
  // always wrap BigInt as a quoted "<digits>n" string.
  it("converts a positive custom-format string to BigInt", () => {
    expect(JSONParse('{"id": "999999999999999999n"}')).toEqual({
      id: 999999999999999999n,
    });
  });

  it("converts a negative custom-format string to BigInt", () => {
    expect(JSONParse('{"id": "-999999999999999999n"}')).toEqual({
      id: -999999999999999999n,
    });
  });

  it("converts custom-format strings found anywhere, including inside arrays", () => {
    expect(JSONParse('{"ids": ["1n", "2n", "not-a-number"]}')).toEqual({
      ids: [1n, 2n, "not-a-number"],
    });
  });

  it("strips a leading zero through BigInt's own parsing", () => {
    expect(JSONParse('{"id": "007n"}')).toEqual({ id: 7n });
  });

  it("leaves sibling properties untouched when one value uses the custom format", () => {
    expect(
      JSONParse('{"id": "999999999999999999n", "name": "Alice", "age": 30}'),
    ).toEqual({ id: 999999999999999999n, name: "Alice", age: 30 });
  });

  // Known false-positive: any plain string that happens to match /^-?\d+n$/
  // is indistinguishable from the lib's own marker and gets coerced to
  // BigInt too, even if the caller meant it as literal text.
  it("(known limitation) coerces an ordinary string that incidentally matches the marker pattern", () => {
    expect(JSONParse('{"code": "123n"}')).toEqual({ code: 123n });
  });
});

describe("JSONParse - automatic detection of oversized numeric literals", () => {
  // The detection regex only fires when the number is immediately followed
  // by one of , ] } with no whitespace in between (see the lookahead in
  // JSONParse.ts). Compact JSON, e.g. from JSON.stringify, satisfies this.
  it("(known bug) throws on a compact object whose value is a 17+ digit literal", () => {
    // The replacement consumes the matched ":" delimiter along with the
    // digits instead of preserving it, corrupting the JSON before the
    // second JSON.parse() call ever runs.
    expect(() => JSONParse('{"id":12345678901234567}')).toThrow(SyntaxError);
  });

  it("(known bug) throws regardless of sign or surrounding whitespace", () => {
    expect(() => JSONParse('{"id": -12345678901234567}')).toThrow(SyntaxError);
    expect(() => JSONParse('{"id":12345678901234567,"name":"Alice"}')).toThrow(
      SyntaxError,
    );
  });

  it("(known bug) throws for a nested object value too", () => {
    expect(() => JSONParse('{"outer":{"id":12345678901234567}}')).toThrow(
      SyntaxError,
    );
  });

  // When whitespace (e.g. pretty-printing) sits between the number and its
  // delimiter, the lookahead never matches, so detection silently does not
  // run at all: the number falls through to native JSON.parse and loses
  // precision instead of throwing or becoming a BigInt.
  it("(known limitation) silently loses precision instead of detecting the number when pretty-printed", () => {
    const result = JSONParse('{\n  "id": 12345678901234567\n}');
    expect(typeof result.id).toBe("number");
    expect(result.id).toBe(12345678901234567); // rounded by JS double conversion
  });

  // A large number that is itself an array element (not a direct property
  // value) is never immediately preceded by '":', so it is never matched by
  // the detection regex either. It is parsed natively and loses precision
  // instead of becoming a BigInt.
  it("(known limitation) does not detect oversized numbers inside arrays", () => {
    const result = JSONParse('{"ids":[12345678901234567,2]}');
    expect(typeof result.ids[0]).toBe("number");
    expect(result.ids[0]).toBe(12345678901234567); // precision lost, stayed a number
    expect(result.ids[1]).toBe(2);
  });

  // The docstring claims 16-digit numbers above MAX_SAFE_INTEGER are also
  // detected, but the regex requires \d{17,}, so a 16-digit overflow is
  // parsed natively and silently loses precision instead.
  it("(known limitation) does not special-case a 16-digit number above MAX_SAFE_INTEGER", () => {
    const result = JSONParse('{"id":9007199254740993}');
    expect(typeof result.id).toBe("number");
    expect(result.id).toBe(9007199254740992); // rounded to the nearest representable double
  });
});

describe("JSONParse - escaped quote guard", () => {
  // The negative lookbehind (?<!\\) exists so an escaped quote inside a
  // string's own content is never mistaken for a real key/value separator.
  // This confirms the guard actually prevents that false match.
  it("does not treat an escaped quote followed by digits as a property delimiter", () => {
    const input = '{"note":"ends with \\":12345678901234567,"}';
    expect(JSONParse(input)).toEqual({
      note: 'ends with ":12345678901234567,',
    });
  });
});

describe("JSONParse - failure paths", () => {
  it("throws a SyntaxError for malformed JSON, same as native JSON.parse", () => {
    expect(() => JSONParse("{a: 1}")).toThrow(SyntaxError);
  });

  it("throws a SyntaxError for empty input", () => {
    expect(() => JSONParse("")).toThrow(SyntaxError);
  });

  it("throws a SyntaxError for an unterminated object", () => {
    expect(() => JSONParse('{"a": 1')).toThrow(SyntaxError);
  });
});