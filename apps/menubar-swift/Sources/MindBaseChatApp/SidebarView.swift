import SwiftUI
import MindBaseChatCore
import UniformTypeIdentifiers

// ChatGPT-style dark sidebar
struct SidebarView: View {
    @ObservedObject var store: ConversationStore
    let onNewChat: () -> Void

    @State private var searchText = ""
    @State private var editingConversationId: UUID?
    @State private var editingTitle = ""
    @State private var hoveredConversationId: UUID?

    private let sidebarBackground = Color(red: 0.1, green: 0.1, blue: 0.1)
    private let itemHoverBackground = Color(red: 0.15, green: 0.15, blue: 0.15)
    private let itemSelectedBackground = Color(red: 0.2, green: 0.2, blue: 0.2)

    var body: some View {
        VStack(spacing: 0) {
            // New Chat Button (ChatGPT style)
            Button(action: onNewChat) {
                HStack {
                    Image(systemName: "plus")
                        .font(.system(size: 14, weight: .medium))
                    Text("New chat")
                        .font(.system(size: 14))
                    Spacer()
                }
                .foregroundColor(.white.opacity(0.9))
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
                .background(Color.white.opacity(0.05))
                .cornerRadius(8)
            }
            .buttonStyle(.plain)
            .padding(.horizontal, 10)
            .padding(.top, 12)
            .padding(.bottom, 8)

            // Search (subtle)
            if !store.conversations.isEmpty {
                HStack(spacing: 8) {
                    Image(systemName: "magnifyingglass")
                        .font(.system(size: 12))
                        .foregroundColor(.white.opacity(0.4))

                    TextField("Search", text: $searchText)
                        .textFieldStyle(.plain)
                        .font(.system(size: 13))
                        .foregroundColor(.white.opacity(0.9))

                    if !searchText.isEmpty {
                        Button {
                            searchText = ""
                        } label: {
                            Image(systemName: "xmark.circle.fill")
                                .font(.system(size: 11))
                                .foregroundColor(.white.opacity(0.4))
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(Color.white.opacity(0.05))
                .cornerRadius(6)
                .padding(.horizontal, 10)
                .padding(.bottom, 8)
            }

            // Conversation list
            ScrollView {
                LazyVStack(spacing: 2) {
                    ForEach(groupedConversations, id: \.key) { group in
                        // Date header
                        Text(group.key)
                            .font(.system(size: 11, weight: .medium))
                            .foregroundColor(.white.opacity(0.4))
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.horizontal, 12)
                            .padding(.top, 12)
                            .padding(.bottom, 4)

                        ForEach(group.conversations) { conversation in
                            ConversationRowView(
                                conversation: conversation,
                                isSelected: store.selectedConversationId == conversation.id,
                                isHovered: hoveredConversationId == conversation.id,
                                isEditing: editingConversationId == conversation.id,
                                editingTitle: $editingTitle,
                                onSelect: { store.selectConversation(conversation.id) },
                                onCommitRename: { commitRename(conversation.id) },
                                onStartRename: { startRename(conversation) },
                                onDelete: { store.deleteConversation(conversation.id) },
                                onExport: { exportConversation(conversation) }
                            )
                            .onHover { isHovered in
                                hoveredConversationId = isHovered ? conversation.id : nil
                            }
                        }
                    }
                }
                .padding(.bottom, 12)
            }

            Spacer(minLength: 0)
        }
        .frame(minWidth: 200, idealWidth: 260, maxWidth: 300)
        .background(sidebarBackground)
    }

    // Filter conversations by search text
    private var filteredConversations: [Conversation] {
        if searchText.isEmpty {
            return store.conversations
        }
        let query = searchText.lowercased()
        return store.conversations.filter { conversation in
            conversation.title.lowercased().contains(query) ||
            conversation.messages.contains { message in
                message.content.lowercased().contains(query)
            }
        }
    }

    // Group conversations by date
    private var groupedConversations: [ConversationGroup] {
        let calendar = Calendar.current
        let now = Date()

        var today: [Conversation] = []
        var yesterday: [Conversation] = []
        var thisWeek: [Conversation] = []
        var thisMonth: [Conversation] = []
        var older: [Conversation] = []

        for conversation in filteredConversations {
            if calendar.isDateInToday(conversation.updatedAt) {
                today.append(conversation)
            } else if calendar.isDateInYesterday(conversation.updatedAt) {
                yesterday.append(conversation)
            } else if let weekAgo = calendar.date(byAdding: .day, value: -7, to: now),
                      conversation.updatedAt > weekAgo {
                thisWeek.append(conversation)
            } else if let monthAgo = calendar.date(byAdding: .month, value: -1, to: now),
                      conversation.updatedAt > monthAgo {
                thisMonth.append(conversation)
            } else {
                older.append(conversation)
            }
        }

        var groups: [ConversationGroup] = []
        if !today.isEmpty { groups.append(ConversationGroup(key: "Today", conversations: today)) }
        if !yesterday.isEmpty { groups.append(ConversationGroup(key: "Yesterday", conversations: yesterday)) }
        if !thisWeek.isEmpty { groups.append(ConversationGroup(key: "Previous 7 Days", conversations: thisWeek)) }
        if !thisMonth.isEmpty { groups.append(ConversationGroup(key: "Previous 30 Days", conversations: thisMonth)) }
        if !older.isEmpty { groups.append(ConversationGroup(key: "Older", conversations: older)) }

        return groups
    }

    private func startRename(_ conversation: Conversation) {
        editingConversationId = conversation.id
        editingTitle = conversation.title
    }

    private func commitRename(_ id: UUID) {
        if !editingTitle.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            store.renameConversation(id, title: editingTitle)
        }
        editingConversationId = nil
        editingTitle = ""
    }

    private func exportConversation(_ conversation: Conversation) {
        let markdown = generateMarkdown(for: conversation)
        let savePanel = NSSavePanel()
        savePanel.allowedContentTypes = [.plainText]
        savePanel.nameFieldStringValue = "\(conversation.title).md"
        savePanel.begin { response in
            if response == .OK, let url = savePanel.url {
                try? markdown.write(to: url, atomically: true, encoding: .utf8)
            }
        }
    }

    private func generateMarkdown(for conversation: Conversation) -> String {
        var md = "# \(conversation.title)\n\n"
        for message in conversation.messages {
            let role = message.role == .user ? "**You**" : "**Assistant**"
            md += "\(role)\n\n\(message.content)\n\n---\n\n"
        }
        return md
    }
}

struct ConversationGroup: Identifiable {
    let key: String
    let conversations: [Conversation]
    var id: String { key }
}

struct ConversationRowView: View {
    let conversation: Conversation
    let isSelected: Bool
    let isHovered: Bool
    let isEditing: Bool
    @Binding var editingTitle: String
    let onSelect: () -> Void
    let onCommitRename: () -> Void
    let onStartRename: () -> Void
    let onDelete: () -> Void
    let onExport: () -> Void

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: "bubble.left")
                .font(.system(size: 12))
                .foregroundColor(.white.opacity(0.5))

            if isEditing {
                TextField("", text: $editingTitle, onCommit: onCommitRename)
                    .textFieldStyle(.plain)
                    .font(.system(size: 14))
                    .foregroundColor(.white)
            } else {
                Text(conversation.title)
                    .font(.system(size: 14))
                    .foregroundColor(.white.opacity(0.9))
                    .lineLimit(1)
            }

            Spacer()

            if isHovered && !isEditing {
                HStack(spacing: 4) {
                    Button(action: onStartRename) {
                        Image(systemName: "pencil")
                            .font(.system(size: 11))
                    }
                    .buttonStyle(.plain)

                    Button(action: onDelete) {
                        Image(systemName: "trash")
                            .font(.system(size: 11))
                    }
                    .buttonStyle(.plain)
                }
                .foregroundColor(.white.opacity(0.5))
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(isSelected ? Color.white.opacity(0.1) : (isHovered ? Color.white.opacity(0.05) : Color.clear))
        )
        .padding(.horizontal, 6)
        .contentShape(Rectangle())
        .onTapGesture(perform: onSelect)
        .contextMenu {
            Button("Rename", action: onStartRename)
            Button("Export", action: onExport)
            Divider()
            Button("Delete", role: .destructive, action: onDelete)
        }
    }
}
