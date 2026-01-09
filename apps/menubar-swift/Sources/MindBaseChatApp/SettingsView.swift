import SwiftUI
import MindBaseChatCore

struct SettingsView: View {
    @ObservedObject var viewModel: ChatViewModel
    @Environment(\.dismiss) private var dismiss

    @State private var tempSystemPrompt: String = ""
    @State private var tempTemperature: Double = 0.7
    @State private var tempMaxTokens: Int = 2048

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Settings")
                    .font(.system(size: 14, weight: .semibold))

                Spacer()

                Button("Done") {
                    saveSettings()
                    dismiss()
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.small)
            }
            .padding()
            .background(Color(nsColor: .windowBackgroundColor))

            Divider()

            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    // Model Section
                    SettingsSection(title: "Model") {
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Text("Current Model")
                                    .font(.system(size: 12))
                                Spacer()
                                Text(viewModel.selectedModel)
                                    .font(.system(size: 12, design: .monospaced))
                                    .foregroundColor(.secondary)
                            }

                            if viewModel.isLoadingModels {
                                HStack {
                                    ProgressView()
                                        .scaleEffect(0.7)
                                    Text("Loading models...")
                                        .font(.system(size: 11))
                                        .foregroundColor(.secondary)
                                }
                            } else {
                                Picker("Select Model", selection: $viewModel.selectedModel) {
                                    ForEach(viewModel.availableModels, id: \.name) { model in
                                        Text(model.displayName)
                                            .tag(model.name)
                                    }
                                }
                                .pickerStyle(.menu)

                                Button("Refresh Models") {
                                    Task { await viewModel.loadModels() }
                                }
                                .font(.system(size: 11))
                            }
                        }
                    }

                    // Generation Settings
                    SettingsSection(title: "Generation") {
                        VStack(alignment: .leading, spacing: 12) {
                            // Temperature
                            VStack(alignment: .leading, spacing: 4) {
                                HStack {
                                    Text("Temperature")
                                        .font(.system(size: 12))
                                    Spacer()
                                    Text(String(format: "%.2f", tempTemperature))
                                        .font(.system(size: 11, design: .monospaced))
                                        .foregroundColor(.secondary)
                                }
                                Slider(value: $tempTemperature, in: 0...2, step: 0.1)
                                Text("Lower = more focused, Higher = more creative")
                                    .font(.system(size: 10))
                                    .foregroundColor(.secondary)
                            }

                            Divider()

                            // Max Tokens
                            VStack(alignment: .leading, spacing: 4) {
                                HStack {
                                    Text("Max Tokens")
                                        .font(.system(size: 12))
                                    Spacer()
                                    Text("\(tempMaxTokens)")
                                        .font(.system(size: 11, design: .monospaced))
                                        .foregroundColor(.secondary)
                                }
                                Slider(value: Binding(
                                    get: { Double(tempMaxTokens) },
                                    set: { tempMaxTokens = Int($0) }
                                ), in: 256...8192, step: 256)
                                Text("Maximum response length")
                                    .font(.system(size: 10))
                                    .foregroundColor(.secondary)
                            }
                        }
                    }

                    // System Prompt
                    SettingsSection(title: "System Prompt") {
                        VStack(alignment: .leading, spacing: 8) {
                            TextEditor(text: $tempSystemPrompt)
                                .font(.system(size: 12))
                                .frame(minHeight: 100, maxHeight: 200)
                                .padding(8)
                                .background(Color(nsColor: .controlBackgroundColor))
                                .cornerRadius(8)

                            HStack {
                                Button("Reset to Default") {
                                    tempSystemPrompt = defaultSystemPrompt
                                }
                                .font(.system(size: 11))

                                Spacer()

                                Text("\(tempSystemPrompt.count) chars")
                                    .font(.system(size: 10))
                                    .foregroundColor(.secondary)
                            }
                        }
                    }

                    // MindBase Integration
                    SettingsSection(title: "MindBase Integration") {
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Text("API URL")
                                    .font(.system(size: 12))
                                Spacer()
                                Text(ProcessInfo.processInfo.environment["MINDBASE_API_URL"] ?? "http://localhost:18003")
                                    .font(.system(size: 11, design: .monospaced))
                                    .foregroundColor(.secondary)
                            }

                            Text("RAG context is automatically fetched from MindBase when available")
                                .font(.system(size: 10))
                                .foregroundColor(.secondary)
                        }
                    }

                    // Keyboard Shortcuts
                    SettingsSection(title: "Keyboard Shortcuts") {
                        VStack(alignment: .leading, spacing: 6) {
                            ShortcutRow(keys: "⌘N", description: "New Chat")
                            ShortcutRow(keys: "⌘⌃S", description: "Toggle Sidebar")
                            ShortcutRow(keys: "⌘.", description: "Stop Generation")
                            ShortcutRow(keys: "⌘⇧R", description: "Retry Last")
                            ShortcutRow(keys: "⌘⇧K", description: "Clear Chat")
                            ShortcutRow(keys: "⌘,", description: "Settings")
                        }
                    }
                }
                .padding()
            }
        }
        .frame(width: 400, height: 550)
        .onAppear {
            tempSystemPrompt = viewModel.systemPrompt
            tempTemperature = viewModel.temperature
            tempMaxTokens = viewModel.maxTokens
        }
    }

    private func saveSettings() {
        viewModel.systemPrompt = tempSystemPrompt
        viewModel.temperature = tempTemperature
        viewModel.maxTokens = tempMaxTokens
    }

    private var defaultSystemPrompt: String {
        """
        You are MindBase, a helpful AI assistant with access to the user's conversation history.
        Answer questions concisely and helpfully. Use the provided context when relevant.
        """
    }
}

struct SettingsSection<Content: View>: View {
    let title: String
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.system(size: 11, weight: .semibold))
                .foregroundColor(.secondary)
                .textCase(.uppercase)

            VStack(alignment: .leading, spacing: 8) {
                content
            }
            .padding(12)
            .background(Color(nsColor: .controlBackgroundColor).opacity(0.5))
            .cornerRadius(8)
        }
    }
}

struct ShortcutRow: View {
    let keys: String
    let description: String

    var body: some View {
        HStack {
            Text(keys)
                .font(.system(size: 11, design: .monospaced))
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
                .background(Color.gray.opacity(0.2))
                .cornerRadius(4)

            Text(description)
                .font(.system(size: 11))
                .foregroundColor(.secondary)

            Spacer()
        }
    }
}
