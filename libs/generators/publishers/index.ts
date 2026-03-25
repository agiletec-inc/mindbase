/**
 * Publisher factory — returns the appropriate publisher for a given platform.
 */

import type { Publisher } from './publisher-interface.js';
import { NotePublisher } from './note-publisher.js';
import { QiitaPublisher } from './qiita-publisher.js';
import { ZennPublisher } from './zenn-publisher.js';

export type { Publisher, PublishResult, Article, PublishOptions } from './publisher-interface.js';

const publishers: Record<string, () => Publisher> = {
  note: () => new NotePublisher(),
  qiita: () => new QiitaPublisher(),
  zenn: () => new ZennPublisher(),
};

export function getPublisher(platform: string): Publisher {
  const factory = publishers[platform];
  if (!factory) {
    throw new Error(
      `Unknown platform: ${platform}. Supported: ${Object.keys(publishers).join(', ')}`
    );
  }
  return factory();
}
