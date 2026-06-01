import { createId } from './createId';

describe('createId helper utility regression tests', () => {
  it('should generate a valid string ID', () => {
    const id = createId();
    expect(typeof id).toBe('string');
    expect(id.length).toBeGreaterThan(0);
  });

  it('should generate completely unique IDs sequentially', () => {
    const ids = new Set();
    const iterations = 100;

    for (let i = 0; i < iterations; i++) {
      ids.add(createId());
    }
    expect(ids.size).toBe(iterations);
  });
});
