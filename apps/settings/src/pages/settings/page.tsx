import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

interface LLMTool {
  id: string;
  name: string;
  category: 'ai-editor' | 'ai-assistant' | 'cli-tool' | 'browser-extension';
  icon: string;
  color: string;
  isInstalled: boolean;
  isEnabled: boolean;
  autoDetect: boolean;
  description: string;
  connectionStatus: 'connected' | 'disconnected' | 'error';
  lastSync?: Date;
}

interface ExternalService {
  id: string;
  name: string;
  category: 'email' | 'storage' | 'communication' | 'task-management';
  icon: string;
  color: string;
  isConnected: boolean;
  description: string;
  permissions: string[];
}

interface Settings {
  theme: 'light' | 'dark' | 'neural';
  autoSync: boolean;
  syncInterval: number;
  showPlatformIcons: boolean;
  timeRange: 'today' | 'week' | 'month' | 'all';
  enableNotifications: boolean;
  dataRetention: number;
  exportFormat: 'json' | 'markdown' | 'csv';
}

export default function SettingsPage() {
  const navigate = useNavigate();
  
  const [activeTab, setActiveTab] = useState<'tools' | 'services' | 'general' | 'data'>('tools');
  
  const [llmTools, setLlmTools] = useState<LLMTool[]>([
    // AI エディター系
    {
      id: 'cursor',
      name: 'Cursor',
      category: 'ai-editor',
      icon: 'ri-code-s-slash-line',
      color: 'blue',
      isInstalled: true,
      isEnabled: true,
      autoDetect: true,
      description: 'AI-powered code editor with advanced completion',
      connectionStatus: 'connected',
      lastSync: new Date(Date.now() - 300000)
    },
    {
      id: 'claude-code',
      name: 'Claude Code',
      category: 'ai-editor',
      icon: 'ri-terminal-line',
      color: 'orange',
      isInstalled: true,
      isEnabled: true,
      autoDetect: true,
      description: 'Anthropic\'s coding assistant',
      connectionStatus: 'connected',
      lastSync: new Date(Date.now() - 600000)
    },
    {
      id: 'vscode',
      name: 'VS Code',
      category: 'ai-editor',
      icon: 'ri-code-line',
      color: 'blue',
      isInstalled: true,
      isEnabled: false,
      autoDetect: true,
      description: 'Visual Studio Code with AI extensions',
      connectionStatus: 'disconnected'
    },
    {
      id: 'windsurf',
      name: 'Windsurf',
      category: 'ai-editor',
      icon: 'ri-windy-line',
      color: 'cyan',
      isInstalled: false,
      isEnabled: false,
      autoDetect: false,
      description: 'Next-generation AI coding environment',
      connectionStatus: 'disconnected'
    },
    {
      id: 'bolt-new',
      name: 'Bolt.new',
      category: 'ai-editor',
      icon: 'ri-flashlight-line',
      color: 'yellow',
      isInstalled: false,
      isEnabled: false,
      autoDetect: false,
      description: 'StackBlitz\'s AI-powered development platform',
      connectionStatus: 'disconnected'
    },
    {
      id: 'replit',
      name: 'Replit',
      category: 'ai-editor',
      icon: 'ri-play-circle-line',
      color: 'green',
      isInstalled: false,
      isEnabled: false,
      autoDetect: false,
      description: 'Collaborative coding with AI assistance',
      connectionStatus: 'disconnected'
    },
    {
      id: 'codex',
      name: 'GitHub Copilot',
      category: 'ai-editor',
      icon: 'ri-github-line',
      color: 'gray',
      isInstalled: false,
      isEnabled: false,
      autoDetect: true,
      description: 'GitHub\'s AI pair programmer',
      connectionStatus: 'disconnected'
    },
    
    // AI アシスタント系
    {
      id: 'claude-desktop',
      name: 'Claude Desktop',
      category: 'ai-assistant',
      icon: 'ri-robot-line',
      color: 'purple',
      isInstalled: true,
      isEnabled: true,
      autoDetect: true,
      description: 'Anthropic\'s desktop AI assistant',
      connectionStatus: 'connected',
      lastSync: new Date(Date.now() - 900000)
    },
    {
      id: 'chatgpt',
      name: 'ChatGPT',
      category: 'ai-assistant',
      icon: 'ri-chat-3-line',
      color: 'green',
      isInstalled: true,
      isEnabled: true,
      autoDetect: false,
      description: 'OpenAI\'s conversational AI',
      connectionStatus: 'connected',
      lastSync: new Date(Date.now() - 1200000)
    },
    {
      id: 'gemini',
      name: 'Google Gemini',
      category: 'ai-assistant',
      icon: 'ri-google-line',
      color: 'red',
      isInstalled: false,
      isEnabled: false,
      autoDetect: false,
      description: 'Google\'s multimodal AI assistant',
      connectionStatus: 'disconnected'
    },
    
    // CLI ツール系
    {
      id: 'gemini-cli',
      name: 'Gemini CLI',
      category: 'cli-tool',
      icon: 'ri-terminal-box-line',
      color: 'red',
      isInstalled: false,
      isEnabled: false,
      autoDetect: true,
      description: 'Command-line interface for Google Gemini',
      connectionStatus: 'disconnected'
    },
    {
      id: 'claude-cli',
      name: 'Claude CLI',
      category: 'cli-tool',
      icon: 'ri-terminal-window-line',
      color: 'purple',
      isInstalled: false,
      isEnabled: false,
      autoDetect: true,
      description: 'Command-line interface for Claude',
      connectionStatus: 'disconnected'
    },
    {
      id: 'openai-cli',
      name: 'OpenAI CLI',
      category: 'cli-tool',
      icon: 'ri-command-line',
      color: 'green',
      isInstalled: false,
      isEnabled: false,
      autoDetect: true,
      description: 'Command-line interface for OpenAI APIs',
      connectionStatus: 'disconnected'
    }
  ]);

  const [externalServices, setExternalServices] = useState<ExternalService[]>([
    // メール系
    {
      id: 'gmail',
      name: 'Gmail',
      category: 'email',
      icon: 'ri-mail-line',
      color: 'red',
      isConnected: false,
      description: 'Google メールサービス',
      permissions: ['メール読み取り', 'メール送信', 'ラベル管理']
    },
    {
      id: 'outlook',
      name: 'Outlook',
      category: 'email',
      icon: 'ri-microsoft-line',
      color: 'blue',
      isConnected: false,
      description: 'Microsoft メールサービス',
      permissions: ['メール読み取り', 'メール送信', 'カレンダー連携']
    },
    
    // ストレージ系
    {
      id: 'google-drive',
      name: 'Google Drive',
      category: 'storage',
      icon: 'ri-google-drive-line',
      color: 'yellow',
      isConnected: false,
      description: 'Google クラウドストレージ',
      permissions: ['ファイル読み取り', 'ファイル作成', 'フォルダ管理']
    },
    {
      id: 'dropbox',
      name: 'Dropbox',
      category: 'storage',
      icon: 'ri-dropbox-line',
      color: 'blue',
      isConnected: false,
      description: 'Dropbox クラウドストレージ',
      permissions: ['ファイル読み取り', 'ファイル同期']
    },
    {
      id: 'onedrive',
      name: 'OneDrive',
      category: 'storage',
      icon: 'ri-cloud-line',
      color: 'blue',
      isConnected: false,
      description: 'Microsoft クラウドストレージ',
      permissions: ['ファイル読み取り', 'ファイル作成']
    },
    
    // コミュニケーション系
    {
      id: 'slack',
      name: 'Slack',
      category: 'communication',
      icon: 'ri-slack-line',
      color: 'purple',
      isConnected: false,
      description: 'チームコミュニケーションツール',
      permissions: ['メッセージ読み取り', 'チャンネル情報', 'ファイル共有']
    },
    {
      id: 'discord',
      name: 'Discord',
      category: 'communication',
      icon: 'ri-discord-line',
      color: 'indigo',
      isConnected: false,
      description: 'ゲーミング・コミュニティプラットフォーム',
      permissions: ['メッセージ読み取り', 'サーバー情報']
    },
    {
      id: 'teams',
      name: 'Microsoft Teams',
      category: 'communication',
      icon: 'ri-team-line',
      color: 'blue',
      isConnected: false,
      description: 'Microsoft チームコラボレーション',
      permissions: ['チャット読み取り', 'ミーティング情報', 'ファイル共有']
    },
    
    // タスク管理系
    {
      id: 'jira',
      name: 'Jira',
      category: 'task-management',
      icon: 'ri-bug-line',
      color: 'blue',
      isConnected: false,
      description: 'Atlassian プロジェクト管理ツール',
      permissions: ['課題読み取り', 'プロジェクト情報', 'コメント']
    },
    {
      id: 'linear',
      name: 'Linear',
      category: 'task-management',
      icon: 'ri-line-chart-line',
      color: 'purple',
      isConnected: false,
      description: 'モダンなプロジェクト管理ツール',
      permissions: ['課題読み取り', 'プロジェクト情報']
    },
    {
      id: 'notion',
      name: 'Notion',
      category: 'task-management',
      icon: 'ri-notion-line',
      color: 'gray',
      isConnected: false,
      description: 'オールインワン作業スペース',
      permissions: ['ページ読み取り', 'データベース', 'ブロック作成']
    },
    {
      id: 'trello',
      name: 'Trello',
      category: 'task-management',
      icon: 'ri-trello-line',
      color: 'blue',
      isConnected: false,
      description: 'カンバン式プロジェクト管理',
      permissions: ['ボード読み取り', 'カード情報', 'リスト管理']
    }
  ]);

  const [settings, setSettings] = useState<Settings>({
    theme: 'light',
    autoSync: true,
    syncInterval: 5,
    showPlatformIcons: true,
    timeRange: 'week',
    enableNotifications: true,
    dataRetention: 365,
    exportFormat: 'json'
  });

  const categoryLabels = {
    'ai-editor': 'AI エディター',
    'ai-assistant': 'AI アシスタント',
    'cli-tool': 'CLI ツール',
    'browser-extension': 'ブラウザ拡張'
  };

  const serviceCategoryLabels = {
    'email': 'メール',
    'storage': 'ストレージ',
    'communication': 'コミュニケーション',
    'task-management': 'タスク管理'
  };

  const toggleTool = (toolId: string) => {
    setLlmTools(prev => prev.map(tool => 
      tool.id === toolId ? { ...tool, isEnabled: !tool.isEnabled } : tool
    ));
  };

  const toggleService = (serviceId: string) => {
    setExternalServices(prev => prev.map(service => 
      service.id === serviceId ? { ...service, isConnected: !service.isConnected } : service
    ));
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected': return 'text-green-600 bg-green-100';
      case 'error': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const formatLastSync = (date?: Date) => {
    if (!date) return '未同期';
    const minutes = Math.floor((Date.now() - date.getTime()) / 60000);
    if (minutes < 1) return '今';
    if (minutes < 60) return `${minutes}分前`;
    const hours = Math.floor(minutes / 60);
    return `${hours}時間前`;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ヘッダー */}
      <div className="bg-white border-b border-gray-200">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate('/')}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg cursor-pointer transition-colors"
              >
                <i className="ri-arrow-left-line text-lg"></i>
              </button>
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                  <i className="ri-brain-line text-white text-lg"></i>
                </div>
                <h1 className="text-xl font-bold text-gray-900" style={{ fontFamily: '"Pacifico", serif' }}>MindBase</h1>
                <span className="text-sm text-gray-500">設定</span>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 cursor-pointer whitespace-nowrap transition-colors">
                <i className="ri-save-line mr-2"></i>
                設定を保存
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="flex">
        {/* サイドバー */}
        <div className="w-64 bg-white border-r border-gray-200 min-h-screen">
          <div className="p-4">
            <nav className="space-y-2">
              {[
                { id: 'tools', label: 'LLM ツール', icon: 'ri-code-line' },
                { id: 'services', label: '外部連携', icon: 'ri-links-line' },
                { id: 'general', label: '一般設定', icon: 'ri-settings-3-line' },
                { id: 'data', label: 'データ管理', icon: 'ri-database-line' }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left cursor-pointer whitespace-nowrap transition-colors ${
                    activeTab === tab.id
                      ? 'bg-blue-50 text-blue-700 border border-blue-200'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  }`}
                >
                  <i className={`${tab.icon} text-lg`}></i>
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* メインコンテンツ */}
        <div className="flex-1 p-6">
          {activeTab === 'tools' && (
            <div className="max-w-4xl">
              <div className="mb-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">LLM ツール管理</h2>
                <p className="text-gray-600">使用しているAIツールの設定と同期状況を管理します</p>
              </div>

              {/* 統計情報 */}
              <div className="grid grid-cols-4 gap-4 mb-8">
                <div className="bg-white rounded-xl p-4 border border-gray-200">
                  <div className="text-2xl font-bold text-gray-900">
                    {llmTools.filter(t => t.isEnabled).length}
                  </div>
                  <div className="text-sm text-gray-500">有効なツール</div>
                </div>
                <div className="bg-white rounded-xl p-4 border border-gray-200">
                  <div className="text-2xl font-bold text-green-600">
                    {llmTools.filter(t => t.connectionStatus === 'connected').length}
                  </div>
                  <div className="text-sm text-gray-500">接続中</div>
                </div>
                <div className="bg-white rounded-xl p-4 border border-gray-200">
                  <div className="text-2xl font-bold text-blue-600">
                    {llmTools.filter(t => t.isInstalled).length}
                  </div>
                  <div className="text-sm text-gray-500">インストール済み</div>
                </div>
                <div className="bg-white rounded-xl p-4 border border-gray-200">
                  <div className="text-2xl font-bold text-orange-600">
                    {llmTools.filter(t => t.autoDetect).length}
                  </div>
                  <div className="text-sm text-gray-500">自動検出</div>
                </div>
              </div>

              {/* カテゴリ別ツール一覧 */}
              {Object.entries(categoryLabels).map(([category, label]) => {
                const categoryTools = llmTools.filter(tool => tool.category === category);
                if (categoryTools.length === 0) return null;

                return (
                  <div key={category} className="mb-8">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                      <i className="ri-folder-line text-blue-600"></i>
                      {label}
                      <span className="text-sm text-gray-500 font-normal">({categoryTools.length})</span>
                    </h3>
                    
                    <div className="grid gap-4">
                      {categoryTools.map((tool) => (
                        <div key={tool.id} className="bg-white rounded-xl p-6 border border-gray-200">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                              <div className={`w-12 h-12 bg-${tool.color}-100 rounded-xl flex items-center justify-center`}>
                                <i className={`${tool.icon} text-${tool.color}-600 text-xl`}></i>
                              </div>
                              <div>
                                <div className="flex items-center gap-3 mb-1">
                                  <h4 className="text-lg font-semibold text-gray-900">{tool.name}</h4>
                                  {tool.isInstalled && (
                                    <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-700 rounded-full">
                                      インストール済み
                                    </span>
                                  )}
                                  {tool.autoDetect && (
                                    <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded-full">
                                      自動検出
                                    </span>
                                  )}
                                </div>
                                <p className="text-sm text-gray-600 mb-2">{tool.description}</p>
                                <div className="flex items-center gap-4 text-xs text-gray-500">
                                  <span className={`px-2 py-1 rounded-full ${getStatusColor(tool.connectionStatus)}`}>
                                    {tool.connectionStatus === 'connected' ? '接続中' : 
                                     tool.connectionStatus === 'error' ? 'エラー' : '未接続'}
                                  </span>
                                  {tool.lastSync && (
                                    <span>最終同期: {formatLastSync(tool.lastSync)}</span>
                                  )}
                                </div>
                              </div>
                            </div>
                            <div className="flex items-center gap-3">
                              <button
                                onClick={() => toggleTool(tool.id)}
                                className={`px-4 py-2 rounded-lg text-sm font-medium cursor-pointer whitespace-nowrap transition-colors ${
                                  tool.isEnabled
                                    ? 'bg-green-100 text-green-700 hover:bg-green-200'
                                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                }`}
                              >
                                {tool.isEnabled ? '有効' : '無効'}
                              </button>
                              <button className="p-2 text-gray-400 hover:text-gray-600 cursor-pointer transition-colors">
                                <i className="ri-settings-line text-lg"></i>
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {activeTab === 'services' && (
            <div className="max-w-4xl">
              <div className="mb-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">外部サービス連携</h2>
                <p className="text-gray-600">メール、ストレージ、コミュニケーションツールとの連携設定</p>
              </div>

              {/* 連携統計 */}
              <div className="grid grid-cols-4 gap-4 mb-8">
                {Object.entries(serviceCategoryLabels).map(([category, label]) => {
                  const categoryServices = externalServices.filter(s => s.category === category);
                  const connectedCount = categoryServices.filter(s => s.isConnected).length;
                  
                  return (
                    <div key={category} className="bg-white rounded-xl p-4 border border-gray-200">
                      <div className="text-2xl font-bold text-gray-900">
                        {connectedCount}/{categoryServices.length}
                      </div>
                      <div className="text-sm text-gray-500">{label}</div>
                    </div>
                  );
                })}
              </div>

              {/* カテゴリ別サービス一覧 */}
              {Object.entries(serviceCategoryLabels).map(([category, label]) => {
                const categoryServices = externalServices.filter(service => service.category === category);
                if (categoryServices.length === 0) return null;

                return (
                  <div key={category} className="mb-8">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                      <i className="ri-links-line text-blue-600"></i>
                      {label}
                      <span className="text-sm text-gray-500 font-normal">({categoryServices.length})</span>
                    </h3>
                    
                    <div className="grid gap-4">
                      {categoryServices.map((service) => (
                        <div key={service.id} className="bg-white rounded-xl p-6 border border-gray-200">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                              <div className={`w-12 h-12 bg-${service.color}-100 rounded-xl flex items-center justify-center`}>
                                <i className={`${service.icon} text-${service.color}-600 text-xl`}></i>
                              </div>
                              <div>
                                <div className="flex items-center gap-3 mb-1">
                                  <h4 className="text-lg font-semibold text-gray-900">{service.name}</h4>
                                  {service.isConnected && (
                                    <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-700 rounded-full">
                                      接続済み
                                    </span>
                                  )}
                                </div>
                                <p className="text-sm text-gray-600 mb-2">{service.description}</p>
                                <div className="flex flex-wrap gap-2">
                                  {service.permissions.map((permission) => (
                                    <span key={permission} className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded">
                                      {permission}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            </div>
                            <div className="flex items-center gap-3">
                              <button
                                onClick={() => toggleService(service.id)}
                                className={`px-4 py-2 rounded-lg text-sm font-medium cursor-pointer whitespace-nowrap transition-colors ${
                                  service.isConnected
                                    ? 'bg-red-100 text-red-700 hover:bg-red-200'
                                    : 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                                }`}
                              >
                                {service.isConnected ? '切断' : '接続'}
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {activeTab === 'general' && (
            <div className="max-w-2xl">
              <div className="mb-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">一般設定</h2>
                <p className="text-gray-600">アプリケーションの基本設定</p>
              </div>

              <div className="space-y-6">
                {/* テーマ設定 */}
                <div className="bg-white rounded-xl p-6 border border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">外観</h3>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-3">テーマ</label>
                      <div className="grid grid-cols-3 gap-3">
                        {[
                          { key: 'light', label: 'ライト', icon: 'ri-sun-line' },
                          { key: 'dark', label: 'ダーク', icon: 'ri-moon-line' },
                          { key: 'neural', label: 'ニューラル', icon: 'ri-brain-line' }
                        ].map((theme) => (
                          <button
                            key={theme.key}
                            onClick={() => setSettings(prev => ({ ...prev, theme: theme.key as any }))}
                            className={`p-4 rounded-lg border cursor-pointer whitespace-nowrap transition-all ${
                              settings.theme === theme.key
                                ? 'border-blue-500 bg-blue-50 text-blue-700'
                                : 'border-gray-300 text-gray-600 hover:border-gray-400'
                            }`}
                          >
                            <i className={`${theme.icon} text-2xl mb-2 block`}></i>
                            <span className="text-sm font-medium">{theme.label}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {/* 同期設定 */}
                <div className="bg-white rounded-xl p-6 border border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">同期設定</h3>
                  <div className="space-y-4">
                    <label className="flex items-center justify-between">
                      <div>
                        <div className="text-sm font-medium text-gray-700">自動同期</div>
                        <div className="text-xs text-gray-500">LLMツールとの会話を自動で取得</div>
                      </div>
                      <input
                        type="checkbox"
                        checked={settings.autoSync}
                        onChange={(e) => setSettings(prev => ({ ...prev, autoSync: e.target.checked }))}
                        className="ml-3"
                      />
                    </label>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">同期間隔</label>
                      <select
                        value={settings.syncInterval}
                        onChange={(e) => setSettings(prev => ({ ...prev, syncInterval: Number(e.target.value) }))}
                        className="w-full px-3 py-2 pr-8 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value={1}>1分</option>
                        <option value={5}>5分</option>
                        <option value={10}>10分</option>
                        <option value={30}>30分</option>
                        <option value={60}>1時間</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* 表示設定 */}
                <div className="bg-white rounded-xl p-6 border border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">表示設定</h3>
                  <div className="space-y-4">
                    <label className="flex items-center justify-between">
                      <div>
                        <div className="text-sm font-medium text-gray-700">プラットフォームアイコン表示</div>
                        <div className="text-xs text-gray-500">どのツールでの会話かを表示</div>
                      </div>
                      <input
                        type="checkbox"
                        checked={settings.showPlatformIcons}
                        onChange={(e) => setSettings(prev => ({ ...prev, showPlatformIcons: e.target.checked }))}
                        className="ml-3"
                      />
                    </label>

                    <label className="flex items-center justify-between">
                      <div>
                        <div className="text-sm font-medium text-gray-700">通知</div>
                        <div className="text-xs text-gray-500">新しい会話の通知を受け取る</div>
                      </div>
                      <input
                        type="checkbox"
                        checked={settings.enableNotifications}
                        onChange={(e) => setSettings(prev => ({ ...prev, enableNotifications: e.target.checked }))}
                        className="ml-3"
                      />
                    </label>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">デフォルト表示期間</label>
                      <select
                        value={settings.timeRange}
                        onChange={(e) => setSettings(prev => ({ ...prev, timeRange: e.target.value as any }))}
                        className="w-full px-3 py-2 pr-8 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="today">今日</option>
                        <option value="week">1週間</option>
                        <option value="month">1ヶ月</option>
                        <option value="all">全期間</option>
                      </select>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'data' && (
            <div className="max-w-2xl">
              <div className="mb-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">データ管理</h2>
                <p className="text-gray-600">会話履歴の保存期間とエクスポート設定</p>
              </div>

              <div className="space-y-6">
                {/* データ保持設定 */}
                <div className="bg-white rounded-xl p-6 border border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">データ保持</h3>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">保存期間</label>
                      <select
                        value={settings.dataRetention}
                        onChange={(e) => setSettings(prev => ({ ...prev, dataRetention: Number(e.target.value) }))}
                        className="w-full px-3 py-2 pr-8 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value={30}>30日</option>
                        <option value={90}>90日</option>
                        <option value={180}>180日</option>
                        <option value={365}>1年</option>
                        <option value={-1}>無制限</option>
                      </select>
                      <p className="text-xs text-gray-500 mt-1">
                        古い会話履歴は自動的に削除されます
                      </p>
                    </div>
                  </div>
                </div>

                {/* エクスポート設定 */}
                <div className="bg-white rounded-xl p-6 border border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">データエクスポート</h3>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">エクスポート形式</label>
                      <select
                        value={settings.exportFormat}
                        onChange={(e) => setSettings(prev => ({ ...prev, exportFormat: e.target.value as any }))}
                        className="w-full px-3 py-2 pr-8 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="json">JSON</option>
                        <option value="markdown">Markdown</option>
                        <option value="csv">CSV</option>
                      </select>
                    </div>
                    
                    <div className="flex gap-3">
                      <button className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 cursor-pointer whitespace-nowrap transition-colors">
                        <i className="ri-download-line mr-2"></i>
                        全データをエクスポート
                      </button>
                      <button className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 cursor-pointer whitespace-nowrap transition-colors">
                        <i className="ri-file-line mr-2"></i>
                        プロジェクト別エクスポート
                      </button>
                    </div>
                  </div>
                </div>

                {/* データ削除 */}
                <div className="bg-white rounded-xl p-6 border border-red-200">
                  <h3 className="text-lg font-semibold text-red-900 mb-4">危険な操作</h3>
                  <div className="space-y-4">
                    <div className="p-4 bg-red-50 rounded-lg">
                      <p className="text-sm text-red-700 mb-3">
                        以下の操作は取り消すことができません。実行前にデータをエクスポートすることを強く推奨します。
                      </p>
                      <div className="flex gap-3">
                        <button className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 cursor-pointer whitespace-nowrap transition-colors">
                          <i className="ri-delete-bin-line mr-2"></i>
                          全データを削除
                        </button>
                        <button className="px-4 py-2 border border-red-300 text-red-700 rounded-lg hover:bg-red-50 cursor-pointer whitespace-nowrap transition-colors">
                          <i className="ri-refresh-line mr-2"></i>
                          設定をリセット
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}