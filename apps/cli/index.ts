#!/usr/bin/env node
/**
 * MindBase CLI
 *
 * Conversation-powered content generation and publishing.
 *
 * Usage:
 *   mindbase generate --topic "Docker" --platform note
 *   mindbase publish  --file article.md --platform note
 *   mindbase search   --query "Docker"
 *   mindbase collect  --source claude-code
 *   mindbase status
 */

const command = process.argv[2];

async function main() {
  switch (command) {
    case 'generate': {
      const { run } = await import('./commands/generate.js');
      await run();
      break;
    }
    case 'publish': {
      const { run } = await import('./commands/publish.js');
      await run();
      break;
    }
    case 'search': {
      const { run } = await import('./commands/search.js');
      await run();
      break;
    }
    case 'collect': {
      const { run } = await import('./commands/collect.js');
      await run();
      break;
    }
    case 'status': {
      const { run } = await import('./commands/status.js');
      await run();
      break;
    }
    case 'hook': {
      const { run } = await import('./commands/hook.js');
      await run();
      break;
    }
    case 'install': {
      const { run } = await import('./commands/install.js');
      await run();
      break;
    }
    case 'uninstall': {
      const { run } = await import('./commands/uninstall.js');
      await run();
      break;
    }
    default:
      console.log(`MindBase CLI v1.0.0

Usage: mindbase <command> [options]

Commands:
  generate   Generate article from conversation data
  publish    Publish article to platform
  search     Search conversations
  collect    Collect conversations from sources
  status     Check service status
  hook       Claude Code lifecycle hook handler (session-end | session-start)
  install    Install Claude Code memory hooks into ~/.claude/settings.json
  uninstall  Remove the Claude Code memory hooks

Examples:
  mindbase generate --topic "Docker-First開発" --platform note
  mindbase publish --file generated/note/article.md --platform note --draft
  mindbase search --query "Docker" --limit 5
  mindbase collect --source claude-code
  mindbase install --api-url http://localhost:18002
  mindbase status`);
      process.exit(command ? 1 : 0);
  }
}

main().catch((error) => {
  console.error(`Error: ${error.message}`);
  process.exit(1);
});
