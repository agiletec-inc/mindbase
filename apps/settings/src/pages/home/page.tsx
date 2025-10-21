

import { useState, useRef, useEffect } from 'react';

interface ConversationSession {
  id: string;
  platform: 'cursor' | 'claude-code' | 'chatgpt' | 'claude-desktop' | 'mindbase';
  projectPath: string;
  projectName: string;
  title: string;
  startTime: Date;
  endTime?: Date;
  messageCount: number;
  summary: string;
  tags: string[];
  importance: number;
  status: 'active' | 'completed' | 'archived';
}

interface Message {
  id: string;
  sessionId: string;
  platform: 'cursor' | 'claude-code' | 'chatgpt' | 'claude-desktop' | 'mindbase';
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  codeBlocks?: string[];
  fileChanges?: string[];
  tags?: string[];
}

interface ProjectStats {
  name: string;
  path: string;
  totalSessions: number;
  totalMessages: number;
  lastActivity: Date;
  platforms: string[];
  mainTopics: string[];
}

interface Settings {
  theme: 'light' | 'dark' | 'neural';
  autoSync: boolean;
  showPlatformIcons: boolean;
  timeRange: 'today' | 'week' | 'month' | 'all';
}

export default function Home() {
  const [sessions, setSessions] = useState<ConversationSession[]>([
    {
      id: '1',
      platform: 'cursor',
      projectPath: '/Users/dev/AGILETECH',
      projectName: 'AGILETECH',
      title: 'React コンポーネント設計について',
      startTime: new Date(Date.now() - 3600000),
      endTime: new Date(Date.now() - 1800000),
      messageCount: 45,
      summary: 'TypeScriptでのReactコンポーネント設計パターンについて議論。カスタムフックの活用とパフォーマンス最適化を検討。',
      tags: ['React', 'TypeScript', 'コンポーネント設計'],
      importance: 9,
      status: 'completed'
    },
    {
      id: '2',
      platform: 'claude-code',
      projectPath: '/Users/dev/AGILETECH',
      projectName: 'AGILETECH',
      title: 'API設計とデータベース構造',
      startTime: new Date(Date.now() - 7200000),
      endTime: new Date(Date.now() - 5400000),
      messageCount: 32,
      summary: 'RESTful API設計とPostgreSQLスキーマ設計について詳細議論。認証システムとデータ正規化を重点的に検討。',
      tags: ['API設計', 'PostgreSQL', '認証'],
      importance: 8,
      status: 'completed'
    },
    {
      id: '3',
      platform: 'chatgpt',
      projectPath: '/Users/dev/AGILETECH',
      projectName: 'AGILETECH',
      title: 'UI/UXデザインシステム構築',
      startTime: new Date(Date.now() - 10800000),
      endTime: new Date(Date.now() - 9000000),
      messageCount: 28,
      summary: 'デザインシステムの構築方針について議論。Tailwind CSSベースのコンポーネントライブラリ設計を検討。',
      tags: ['UI/UX', 'デザインシステム', 'Tailwind'],
      importance: 7,
      status: 'completed'
    },
    {
      id: '4',
      platform: 'claude-desktop',
      projectPath: '/Users/dev/mindbase-mcp',
      projectName: 'mindbase-mcp',
      title: 'MCP統合とRAG実装について',
      startTime: new Date(Date.now() - 14400000),
      endTime: new Date(Date.now() - 12600000),
      messageCount: 67,
      summary: 'pgvectorとSupabaseを活用したRAG統合システムの実装について詳細議論。MCPネイティブAPIの設計とベクトル検索の最適化を検討。',
      tags: ['MCP', 'RAG', 'pgvector', 'Supabase'],
      importance: 9,
      status: 'completed'
    },
    {
      id: '5',
      platform: 'cursor',
      projectPath: '/Users/dev/readdy-website',
      projectName: 'readdy-website',
      title: 'Readdy公式サイトのリニューアル',
      startTime: new Date(Date.now() - 18000000),
      endTime: new Date(Date.now() - 16200000),
      messageCount: 23,
      summary: 'Readdy公式サイトのデザインリニューアルについて。ユーザビリティ向上とコンバージョン最適化を中心に議論。',
      tags: ['Webデザイン', 'UX', 'マーケティング'],
      importance: 6,
      status: 'completed'
    },
    {
      id: '6',
      platform: 'claude-code',
      projectPath: '/Users/dev/AGILETECH',
      projectName: 'AGILETECH',
      title: '現在のセッション - パフォーマンス最適化',
      startTime: new Date(Date.now() - 1800000),
      messageCount: 12,
      summary: 'React アプリケーションのパフォーマンス最適化について議論中...',
      tags: ['パフォーマンス', 'React', '最適化'],
      importance: 8,
      status: 'active'
    },
    {
      id: '7',
      platform: 'chatgpt',
      projectPath: '/Users/dev/ai-tools-comparison',
      projectName: 'ai-tools-comparison',
      title: 'AI開発ツール比較分析',
      startTime: new Date(Date.now() - 21600000),
      endTime: new Date(Date.now() - 19800000),
      messageCount: 34,
      summary: 'Cursor、Claude Code、GitHub Copilotの機能比較。各ツールの特徴と使い分けについて分析。',
      tags: ['AI開発ツール', '比較分析', '開発効率'],
      importance: 5,
      status: 'completed'
    }
  ]);

  const [activeProject, setActiveProject] = useState<string>('AGILETECH');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPlatform, setSelectedPlatform] = useState<string>('all');
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState<Settings>({
    theme: 'light',
    autoSync: true,
    showPlatformIcons: true,
    timeRange: 'week'
  });

  // プロジェクト統計の計算
  const projectStats: ProjectStats[] = Array.from(
    sessions.reduce((acc, session) => {
      const existing = acc.get(session.projectName);
      if (existing) {
        existing.totalSessions++;
        existing.totalMessages += session.messageCount;
        if (session.startTime > existing.lastActivity) {
          existing.lastActivity = session.startTime;
        }
        if (!existing.platforms.includes(session.platform)) {
          existing.platforms.push(session.platform);
        }
        session.tags.forEach(tag => {
          if (!existing.mainTopics.includes(tag)) {
            existing.mainTopics.push(tag);
          }
        });
      } else {
        acc.set(session.projectName, {
          name: session.projectName,
          path: session.projectPath,
          totalSessions: 1,
          totalMessages: session.messageCount,
          lastActivity: session.startTime,
          platforms: [session.platform],
          mainTopics: [...session.tags]
        });
      }
      return acc;
    }, new Map<string, ProjectStats>())
  ).map(([_, stats]) => stats);

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
  };

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('ja-JP', { month: 'short', day: 'numeric' });
  };

  const formatDuration = (start: Date, end?: Date) => {
    if (!end) return '進行中';
    const minutes = Math.floor((end.getTime() - start.getTime()) / 60000);
    if (minutes < 60) return `${minutes}分`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}時間${mins}分` : `${hours}時間`;
  };

  // プラットフォーム情報
  const platformInfo = {
    cursor: { name: 'Cursor', icon: 'ri-code-s-slash-line', color: 'blue' },
    'claude-code': { name: 'Claude Code', icon: 'ri-terminal-line', color: 'orange' },
    chatgpt: { name: 'ChatGPT', icon: 'ri-chat-3-line', color: 'green' },
    'claude-desktop': { name: 'Claude Desktop', icon: 'ri-robot-line', color: 'purple' },
    mindbase: { name: 'MindBase', icon: 'ri-brain-line', color: 'indigo' }
  };

  // テーマスタイル
  const getThemeStyles = () => {
    switch (settings.theme) {
      case 'dark':
        return {
          bg: 'bg-gray-900',
          header: 'bg-gray-800 border-gray-700',
          card: 'bg-gray-700 border-gray-600',
          text: 'text-gray-100',
          textSecondary: 'text-gray-400'
        };
      case 'neural':
        return {
          bg: 'bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900',
          header: 'bg-black/20 backdrop-blur-sm border-purple-500/20',
          card: 'bg-black/10 backdrop-blur-sm border-purple-500/20',
          text: 'text-purple-100',
          textSecondary: 'text-purple-300'
        };
      default:
        return {
          bg: 'bg-gray-50',
          header: 'bg-white border-gray-200',
          card: 'bg-white border-gray-200',
          text: 'text-gray-900',
          textSecondary: 'text-gray-500'
        };
    }
  };

  const themeStyles = getThemeStyles();

  // フィルタリング
  const filteredSessions = sessions.filter(session => {
    const matchesProject = session.projectName === activeProject;
    const matchesPlatform = selectedPlatform === 'all' || session.platform === selectedPlatform;
    const matchesSearch = !searchQuery || 
      session.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      session.summary.toLowerCase().includes(searchQuery.toLowerCase()) ||
      session.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
    
    return matchesProject && matchesPlatform && matchesSearch;
  }).sort((a, b) => b.startTime.getTime() - a.startTime.getTime());

  const handleSettingsChange = (key: keyof Settings, value: any) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className={`min-h-screen ${themeStyles.bg} flex flex-col`}>
      {/* 設定パネル */}
      {showSettings && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className={`${themeStyles.card} rounded-2xl p-6 w-96 max-h-[80vh] overflow-y-auto`}>
            <div className="flex items-center justify-between mb-6">
              <h2 className={`text-lg font-semibold ${themeStyles.text}`}>MindBase 設定</h2>
              <button
                onClick={() => setShowSettings(false)}
                className={`p-2 ${themeStyles.textSecondary} hover:${themeStyles.text} rounded-lg cursor-pointer transition-colors`}
              >
                <i className="ri-close-line text-lg"></i>
              </button>
            </div>

            <div className="space-y-6">
              {/* テーマ設定 */}
              <div>
                <label className={`block text-sm font-medium ${themeStyles.text} mb-3`}>テーマ</label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { key: 'light', label: 'ライト', icon: 'ri-sun-line' },
                    { key: 'dark', label: 'ダーク', icon: 'ri-moon-line' },
                    { key: 'neural', label: 'ニューラル', icon: 'ri-brain-line' }
                  ].map((theme) => (
                    <button
                      key={theme.key}
                      onClick={() => handleSettingsChange('theme', theme.key)}
                      className={`p-3 rounded-lg border cursor-pointer whitespace-nowrap transition-all ${
                        settings.theme === theme.key
                          ? 'border-blue-500 bg-blue-50 text-blue-700'
                          : `border-gray-300 ${themeStyles.textSecondary} hover:border-gray-400`
                      }`}
                    >
                      <i className={`${theme.icon} text-lg mb-1 block`}></i>
                      <span className="text-xs">{theme.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* 機能設定 */}
              <div>
                <label className={`block text-sm font-medium ${themeStyles.text} mb-3`}>機能設定</label>
                <div className="space-y-3">
                  {[
                    { key: 'autoSync', label: '自動同期', desc: 'LLMツールとの会話を自動取得' },
                    { key: 'showPlatformIcons', label: 'プラットフォーム表示', desc: 'どのツールでの会話かを表示' }
                  ].map((setting) => (
                    <label key={setting.key} className="flex items-center justify-between cursor-pointer">
                      <div>
                        <div className={`text-sm ${themeStyles.text}`}>{setting.label}</div>
                        <div className={`text-xs ${themeStyles.textSecondary}`}>{setting.desc}</div>
                      </div>
                      <input
                        type="checkbox"
                        checked={settings[setting.key as keyof Settings] as boolean}
                        onChange={(e) => handleSettingsChange(setting.key as keyof Settings, e.target.checked)}
                        className="ml-3"
                      />
                    </label>
                  ))}
                </div>
              </div>

              {/* 時間範囲 */}
              <div>
                <label className={`block text-sm font-medium ${themeStyles.text} mb-3`}>表示期間</label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { key: 'today', label: '今日' },
                    { key: 'week', label: '1週間' },
                    { key: 'month', label: '1ヶ月' },
                    { key: 'all', label: '全期間' }
                  ].map((range) => (
                    <button
                      key={range.key}
                      onClick={() => handleSettingsChange('timeRange', range.key)}
                      className={`p-2 text-xs font-medium rounded-lg cursor-pointer whitespace-nowrap transition-colors ${
                        settings.timeRange === range.key
                          ? 'bg-blue-600 text-white'
                          : `${themeStyles.textSecondary} hover:${themeStyles.text} border border-gray-300`
                      }`}
                    >
                      {range.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-gray-200">
              <button
                onClick={() => setShowSettings(false)}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 cursor-pointer whitespace-nowrap transition-colors mb-3"
              >
                設定を保存
              </button>
              <button
                onClick={() => {
                  setShowSettings(false);
                  window.REACT_APP_NAVIGATE('/settings');
                }}
                className="w-full px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 cursor-pointer whitespace-nowrap transition-colors"
              >
                詳細設定を開く
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ヘッダー */}
      <div className={`${themeStyles.header} border-b`}>
        <div className="px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className={`w-8 h-8 ${settings.theme === 'neural' ? 'bg-gradient-to-br from-purple-500 to-blue-600' : 'bg-gradient-to-br from-blue-500 to-purple-600'} rounded-lg flex items-center justify-center`}>
                <i className="ri-brain-line text-white text-lg"></i>
              </div>
              <h1 className={`text-xl font-bold ${themeStyles.text}`} style={{ fontFamily: '"Pacifico", serif' }}>MindBase</h1>
              <span className={`text-sm ${themeStyles.textSecondary}`}>LLM横断会話履歴管理</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 text-sm">
                <div className={`w-2 h-2 ${settings.autoSync ? 'bg-green-500 animate-pulse' : 'bg-gray-400'} rounded-full`}></div>
                <span className={themeStyles.textSecondary}>
                  {settings.autoSync ? '自動同期中' : '手動同期'}
                </span>
              </div>
              <button className={`p-2 ${themeStyles.textSecondary} hover:${themeStyles.text} ${settings.theme === 'dark' ? 'hover:bg-gray-700' : settings.theme === 'neural' ? 'hover:bg-black/20' : 'hover:bg-gray-100'} rounded-lg cursor-pointer transition-colors`}>
                <i className="ri-refresh-line text-lg"></i>
              </button>
              <button 
                onClick={() => setShowSettings(true)}
                className={`p-2 ${themeStyles.textSecondary} hover:${themeStyles.text} ${settings.theme === 'dark' ? 'hover:bg-gray-700' : settings.theme === 'neural' ? 'hover:bg-black/20' : 'hover:bg-gray-100'} rounded-lg cursor-pointer transition-colors`}
              >
                <i className="ri-settings-3-line text-lg"></i>
              </button>
            </div>
          </div>

          {/* プロジェクトタブ */}
          <div className="flex items-center gap-1 mb-4">
            {projectStats.map((project) => (
              <button
                key={project.name}
                onClick={() => setActiveProject(project.name)}
                className={`px-4 py-2 rounded-lg text-sm font-medium cursor-pointer whitespace-nowrap transition-all ${
                  activeProject === project.name
                    ? 'bg-blue-600 text-white shadow-md'
                    : `${themeStyles.textSecondary} hover:${themeStyles.text} ${settings.theme === 'dark' ? 'hover:bg-gray-700' : settings.theme === 'neural' ? 'hover:bg-black/20' : 'hover:bg-gray-100'}`
                }`}
              >
                <i className="ri-folder-line mr-2"></i>
                {project.name}
                <span className={`ml-2 px-2 py-1 text-xs rounded-full ${
                  activeProject === project.name 
                    ? 'bg-blue-500 text-blue-100' 
                    : 'bg-gray-200 text-gray-600'
                }`}>
                  {project.totalSessions}
                </span>
              </button>
            ))}
          </div>

          {/* 検索・フィルター */}
          <div className="flex items-center gap-4">
            <div className="flex-1 relative">
              <i className={`ri-search-line absolute left-3 top-1/2 transform -translate-y-1/2 ${themeStyles.textSecondary} text-sm`}></i>
              <input
                type="text"
                placeholder="会話履歴を検索..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className={`w-full pl-10 pr-4 py-2 border ${settings.theme === 'dark' ? 'border-gray-600 bg-gray-700 text-gray-100' : settings.theme === 'neural' ? 'border-purple-500/30 bg-black/20 text-purple-100 placeholder-purple-300' : 'border-gray-300 bg-white'} rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
              />
            </div>
            <select
              value={selectedPlatform}
              onChange={(e) => setSelectedPlatform(e.target.value)}
              className={`px-3 py-2 pr-8 border ${settings.theme === 'dark' ? 'border-gray-600 bg-gray-700 text-gray-100' : settings.theme === 'neural' ? 'border-purple-500/30 bg-black/20 text-purple-100' : 'border-gray-300 bg-white'} rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
            >
              <option value="all">全プラットフォーム</option>
              {Object.entries(platformInfo).map(([key, info]) => (
                <option key={key} value={key}>{info.name}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* メインタイムライン */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto p-6">
          {/* プロジェクト情報 */}
          <div className={`${themeStyles.card} rounded-xl p-6 mb-6`}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                  <i className="ri-folder-line text-white text-xl"></i>
                </div>
                <div>
                  <h2 className={`text-xl font-semibold ${themeStyles.text}`}>{activeProject}</h2>
                  <p className={`text-sm ${themeStyles.textSecondary}`}>
                    {projectStats.find(p => p.name === activeProject)?.path}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <div className={`text-2xl font-bold ${themeStyles.text}`}>
                  {filteredSessions.length}
                </div>
                <div className={`text-sm ${themeStyles.textSecondary}`}>セッション</div>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className={`text-lg font-semibold ${themeStyles.text}`}>
                  {filteredSessions.reduce((sum, s) => sum + s.messageCount, 0)}
                </div>
                <div className={`text-xs ${themeStyles.textSecondary}`}>総メッセージ数</div>
              </div>
              <div className="text-center">
                <div className={`text-lg font-semibold ${themeStyles.text}`}>
                  {Array.from(new Set(filteredSessions.map(s => s.platform))).length}
                </div>
                <div className={`text-xs ${themeStyles.textSecondary}`}>使用ツール</div>
              </div>
              <div className="text-center">
                <div className={`text-lg font-semibold ${themeStyles.text}`}>
                  {filteredSessions.filter(s => s.status === 'active').length}
                </div>
                <div className={`text-xs ${themeStyles.textSecondary}`}>進行中</div>
              </div>
              <div className="text-center">
                <div className={`text-lg font-semibold ${themeStyles.text}`}>
                  {Math.round(filteredSessions.reduce((sum, s) => sum + s.importance, 0) / filteredSessions.length * 10) / 10 || 0}
                </div>
                <div className={`text-xs ${themeStyles.textSecondary}`}>平均重要度</div>
              </div>
            </div>
          </div>

          {/* タイムライン */}
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className={`text-lg font-semibold ${themeStyles.text}`}>
                会話タイムライン ({filteredSessions.length}件)
              </h3>
              <div className="flex gap-2">
                {Array.from(new Set(filteredSessions.map(s => s.platform))).map(platform => (
                  <div key={platform} className={`flex items-center gap-2 px-3 py-1 rounded-full bg-${platformInfo[platform].color}-100 text-${platformInfo[platform].color}-700`}>
                    <i className={`${platformInfo[platform].icon} text-sm`}></i>
                    <span className="text-xs font-medium">{platformInfo[platform].name}</span>
                    <span className="text-xs">
                      {filteredSessions.filter(s => s.platform === platform).length}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="relative">
              <div className={`absolute left-8 top-0 bottom-0 w-px ${settings.theme === 'dark' ? 'bg-gray-600' : settings.theme === 'neural' ? 'bg-purple-500/30' : 'bg-gray-200'}`}></div>
              
              {filteredSessions.map((session, index) => (
                <div key={session.id} className="relative pb-8 last:pb-0">
                  <div className={`absolute left-6 w-4 h-4 bg-${platformInfo[session.platform].color}-500 rounded-full border-2 ${settings.theme === 'dark' ? 'border-gray-900' : settings.theme === 'neural' ? 'border-purple-900' : 'border-gray-50'} flex items-center justify-center ${session.status === 'active' ? 'animate-pulse' : ''}`}>
                    <i className={`${platformInfo[session.platform].icon} text-xs text-white`}></i>
                  </div>

                  <div className="ml-16">
                    <div className={`${themeStyles.card} rounded-xl p-6 cursor-pointer transition-all hover:shadow-lg`}>
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h4 className={`text-lg font-semibold ${themeStyles.text}`}>
                              {session.title}
                            </h4>
                            {session.status === 'active' && (
                              <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-700 rounded-full animate-pulse">
                                進行中
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-3 text-sm mb-3">
                            <span className={`px-3 py-1 rounded-full bg-${platformInfo[session.platform].color}-100 text-${platformInfo[session.platform].color}-700 font-medium`}>
                              {platformInfo[session.platform].name}
                            </span>
                            <span className={themeStyles.textSecondary}>
                              {formatDate(session.startTime)} {formatTime(session.startTime)}
                            </span>
                            <span className={themeStyles.textSecondary}>
                              {formatDuration(session.startTime, session.endTime)}
                            </span>
                          </div>
                        </div>
                        <div className="flex flex-col items-end gap-2">
                          <div className={`w-3 h-3 rounded-full ${
                            session.importance >= 8 ? 'bg-red-500' : 
                            session.importance >= 6 ? 'bg-yellow-500' : 'bg-green-500'
                          }`}></div>
                          <span className={`text-xs ${themeStyles.textSecondary}`}>
                            重要度 {session.importance}
                          </span>
                        </div>
                      </div>

                      <p className={`text-sm ${themeStyles.textSecondary} mb-4 leading-relaxed`}>
                        {session.summary}
                      </p>

                      <div className="flex items-center justify-between">
                        <div className="flex flex-wrap gap-2">
                          {session.tags.map((tag) => (
                            <span key={tag} className="px-3 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-700">
                              {tag}
                            </span>
                          ))}
                        </div>
                        <div className="flex items-center gap-4 text-sm">
                          <span className={`${themeStyles.textSecondary} flex items-center gap-1`}>
                            <i className="ri-message-3-line"></i>
                            {session.messageCount} メッセージ
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}

              {filteredSessions.length === 0 && (
                <div className={`text-center py-12 ${themeStyles.textSecondary}`}>
                  <i className="ri-history-line text-4xl mb-4 block"></i>
                  <h3 className="text-lg font-medium mb-2">該当する会話履歴が見つかりません</h3>
                  <p className="text-sm">検索条件やフィルタを変更してみてください</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

