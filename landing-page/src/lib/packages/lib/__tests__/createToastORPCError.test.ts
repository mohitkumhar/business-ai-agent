import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { createToastORPCError } from '../createToastORPCError';

describe('createToastORPCError', () => {
  it('should return an ORPCError for a string error', async () => {
    const result = await createToastORPCError('Something went wrong', 'TestCtx');
    assert.ok(result instanceof Error);
    assert.equal(result.message, 'Something went wrong');
    assert.equal((result as any).code, 'INTERNAL_SERVER_ERROR');
    assert.deepEqual((result as any).data, {
      context: 'TestCtx',
      details: undefined,
    });
  });

  it('should return an ORPCError for an Error object', async () => {
    const result = await createToastORPCError(new Error('Boom'), 'ErrCtx');
    assert.ok(result instanceof Error);
    assert.equal(result.message, '[undefined] Boom');
    assert.equal((result as any).code, 'INTERNAL_SERVER_ERROR');
    assert.deepEqual((result as any).data, {
      context: 'ErrCtx',
      details: undefined,
    });
  });

  it('should handle missing context gracefully', async () => {
    const result = await createToastORPCError('minimal error');
    assert.ok(result instanceof Error);
    assert.equal(result.message, 'minimal error');
    assert.deepEqual((result as any).data, {
      context: undefined,
      details: undefined,
    });
  });
});
