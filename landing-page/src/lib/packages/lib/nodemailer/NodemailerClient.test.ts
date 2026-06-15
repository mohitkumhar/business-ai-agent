import { describe, expect, it, mock, beforeEach } from "bun:test";
import { Effect, Layer, ConfigProvider, Exit, Cause } from "effect";
import { NodemailerClientLayer, NodemailerClient, NodemailerError } from "./NodemailerClient";

import type { Mock } from "bun:test";

const mockSendMail = mock((..._args: any[]) => Promise.resolve());
const mockCreateTransport = mock((options: any, defaults: any) => {
  return {
    sendMail: mockSendMail,
  };
});

mock.module("nodemailer", () => {
  return {
    createTransport: mockCreateTransport,
  };
});

import * as nodemailer from "nodemailer";

describe("NodemailerClientLayer", () => {
  beforeEach(() => {
    mockSendMail.mockClear();
    mockCreateTransport.mockClear();
  });

  const validConfig = new Map([
    ["SMTP_HOST", "smtp.example.com"],
    ["SMTP_PORT", "587"],
    ["SMTP_SECURE", "false"],
    ["SMTP_IGNORE_TLS", "true"],
    ["SMTP_USERNAME", "testuser"],
    ["SMTP_PASSWORD", "testpass"],
    ["NEXT_PUBLIC_SMTP_FROM", "test@example.com"],
  ]);

  const testConfigProvider = ConfigProvider.fromMap(validConfig);

  const setupClient = () =>
    Effect.provide(NodemailerClient, NodemailerClientLayer).pipe(
      Effect.provide(Layer.setConfigProvider(testConfigProvider))
    );

  describe("Initialization", () => {
    it("should initialize createTransport with correct config", async () => {
      await Effect.runPromise(setupClient());
      
      expect(mockCreateTransport).toHaveBeenCalledTimes(1);
      expect(mockCreateTransport).toHaveBeenCalledWith(
        {
          host: "smtp.example.com",
          port: 587,
          secure: false,
          ignoreTLS: true,
          auth: {
            user: "testuser",
            pass: "testpass",
          },
        },
        {
          from: "test@example.com",
        }
      );
    });

    it("should fail to initialize if required config is missing", async () => {
      const emptyConfigProvider = ConfigProvider.fromMap(new Map());
      
      const result = await Effect.runPromiseExit(
        Effect.provide(NodemailerClient, NodemailerClientLayer).pipe(
          Effect.provide(Layer.setConfigProvider(emptyConfigProvider))
        )
      );
      
      expect(Exit.isFailure(result)).toBe(true);
    });

    it("should use default boolean values for secure and ignoreTLS when missing", async () => {
      const partialConfig = new Map(validConfig);
      partialConfig.delete("SMTP_SECURE");
      partialConfig.delete("SMTP_IGNORE_TLS");

      await Effect.runPromise(
        Effect.provide(NodemailerClient, NodemailerClientLayer).pipe(
          Effect.provide(Layer.setConfigProvider(ConfigProvider.fromMap(partialConfig)))
        )
      );

      expect(mockCreateTransport).toHaveBeenCalledTimes(1);
      const callArgs = mockCreateTransport.mock.calls[0][0];
      expect(callArgs.secure).toBe(false);
      expect(callArgs.ignoreTLS).toBe(undefined);
    });
  });

  describe("sendMail", () => {
    it("should successfully send an email", async () => {
      mockSendMail.mockResolvedValueOnce({ messageId: "123" });
      
      const client = await Effect.runPromise(setupClient());
      
      const options = { to: "user@example.com", subject: "Hello", text: "World" };
      await Effect.runPromise(client.sendMail(options));
      
      expect(mockSendMail).toHaveBeenCalledTimes(1);
      expect(mockSendMail).toHaveBeenCalledWith(options);
    });

    it("should return NodemailerError when sendMail rejects", async () => {
      const error = new Error("SMTP connection failed");
      mockSendMail.mockRejectedValueOnce(error);
      
      const client = await Effect.runPromise(setupClient());
      
      const options = { to: "user@example.com", subject: "Hello" };
      
      const result = await Effect.runPromiseExit(client.sendMail(options));
      
      expect(Exit.isFailure(result)).toBe(true);
      if (Exit.isFailure(result)) {
        const cause = result.cause;
        if (Cause.isFailType(cause)) {
          const expectedError = cause.error as NodemailerError;
          expect(expectedError._tag).toBe("@typebot/NodemailerError");
          expect(expectedError.cause).toBe(error);
        } else {
          throw new Error("Expected a Fail cause");
        }
      }
    });

    it("should return NodemailerError when sendMail throws synchronously", async () => {
      const error = new Error("Sync throw");
      mockSendMail.mockImplementationOnce(() => {
        throw error;
      });
      
      const client = await Effect.runPromise(setupClient());
      const result = await Effect.runPromiseExit(client.sendMail({ to: "user@example.com" }));
      
      expect(Exit.isFailure(result)).toBe(true);
      if (Exit.isFailure(result)) {
        const cause = result.cause;
        if (Cause.isFailType(cause)) {
          const expectedError = cause.error as NodemailerError;
          expect(expectedError._tag).toBe("@typebot/NodemailerError");
          expect(expectedError.cause).toBe(error);
        } else {
          throw new Error("Expected a Fail cause");
        }
      }
    });
  });
});
