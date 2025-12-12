import SwiftUI
import MindBaseChatCore

@main
struct MindBaseChatApp: App {
    @StateObject private var viewModel = ChatViewModel()
    @StateObject private var conversationStore = ConversationStore()
    @State private var columnVisibility: NavigationSplitViewVisibility = .all

    var body: some Scene {
        WindowGroup {
            NavigationSplitView(columnVisibility: $columnVisibility) {
                SidebarView(store: conversationStore) {
                    createNewChat()
                }
            } detail: {
                ChatView(viewModel: viewModel)
            }
            .navigationSplitViewStyle(.balanced)
            .onChange(of: conversationStore.selectedConversationId) { _, newId in
                loadConversation(id: newId)
            }
            .onChange(of: viewModel.messages) { _, newMessages in
                saveCurrentConversation(messages: newMessages)
            }
        }
        .windowStyle(.hiddenTitleBar)
        .defaultSize(width: 1000, height: 650)
        .commands {
            CommandGroup(replacing: .newItem) {
                Button("New Chat") {
                    createNewChat()
                }
                .keyboardShortcut("n", modifiers: .command)
            }

            CommandMenu("Chat") {
                Button("Toggle Sidebar") {
                    withAnimation {
                        columnVisibility = columnVisibility == .all ? .detailOnly : .all
                    }
                }
                .keyboardShortcut("s", modifiers: [.command, .control])

                Divider()

                Button("Stop Generation") {
                    viewModel.stop()
                }
                .keyboardShortcut(".", modifiers: .command)
                .disabled(!viewModel.isStreaming)

                Button("Retry Last") {
                    viewModel.retry()
                }
                .keyboardShortcut("r", modifiers: [.command, .shift])
                .disabled(viewModel.messages.isEmpty || viewModel.isStreaming)

                Divider()

                Button("Clear Chat") {
                    viewModel.clearChat()
                }
                .keyboardShortcut("k", modifiers: [.command, .shift])
            }
        }
    }

    private func createNewChat() {
        // Save current conversation first
        if let currentId = conversationStore.selectedConversationId, !viewModel.messages.isEmpty {
            let storedMessages = viewModel.messages.map { $0.toStored() }
            conversationStore.updateConversation(currentId, messages: storedMessages)
        }

        // Create new conversation
        let newConversation = conversationStore.createConversation()
        viewModel.clearChat()
        conversationStore.selectConversation(newConversation.id)
    }

    private func loadConversation(id: UUID?) {
        guard let id = id,
              let conversation = conversationStore.conversations.first(where: { $0.id == id }) else {
            return
        }

        // Load messages into view model
        viewModel.messages = conversation.messages.map { $0.toChatMessage() }
    }

    private func saveCurrentConversation(messages: [ChatMessage]) {
        guard let currentId = conversationStore.selectedConversationId,
              !messages.isEmpty else { return }

        let storedMessages = messages.map { $0.toStored() }
        conversationStore.updateConversation(currentId, messages: storedMessages)
    }
}
