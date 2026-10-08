import { createInterface } from 'node:readline';
import { Blaze } from '@sourcemeta/blaze';

const evaluators = new Map();
for await (const line of createInterface({ input: process.stdin })) {
  try {
    const message = JSON.parse(line, Blaze.reviver);
    let response;
    if (message.op === 'compile') {
      evaluators.set(message.id, new Blaze(message.template));
      response = { compiled: true };
    } else if (message.op === 'drop') {
      evaluators.delete(message.id);
      response = { dropped: true };
    } else if (message.op === 'validate') {
      const evaluator = evaluators.get(message.id);
      if (!evaluator) throw new Error('Unknown compiled schema');
      response = { valid: evaluator.validate(message.instance) };
    } else {
      throw new Error('Unknown operation');
    }
    process.stdout.write(JSON.stringify(response) + '\n');
  } catch (error) {
    process.stdout.write(JSON.stringify({ error: String(error.message) }) + '\n');
  }
}
