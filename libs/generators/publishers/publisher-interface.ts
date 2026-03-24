/**
 * Publisher interface for multi-platform article publishing.
 */

export interface Article {
  title: string;
  content: string;
  tags: string[];
}

export interface PublishOptions {
  draft?: boolean;
}

export interface PublishResult {
  success: boolean;
  url?: string;
  id?: string;
  method: 'api' | 'file' | 'git';
  filePath?: string;
  error?: string;
}

export interface Publisher {
  publish(article: Article, options: PublishOptions): Promise<PublishResult>;
  preview(article: Article): string;
}
