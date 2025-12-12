import SwiftUI
import MindBaseChatCore

struct SidebarView: View {
    @ObservedObject var store: ConversationStore
    let onNewChat: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            // Header with new chat button
            HStack {
                Text("Chats")
                    .font(.system(size: 13, weight: .semibold))

                Spacer()

                Button(action: onNewChat) {
                    Image(systemName: "square.and.pencil")
                        .font(.system(size: 12))
                }
                .buttonStyle(.plain)
                .help("New Chat (Cmd+N)")
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
            .background(Color(nsColor: .windowBackgroundColor))

            Divider()

            // Conversation list
            if store.conversations.isEmpty {
                VStack(spacing: 8) {
                    Spacer()
                    Image(systemName: "bubble.left.and.bubble.right")
                        .font(.system(size: 24))
                        .foregroundColor(.secondary)
                    Text("No conversations")
                        .font(.system(size: 12))
                        .foregroundColor(.secondary)
                    Spacer()
                }
                .frame(maxWidth: .infinity)
            } else {
                List(selection: $store.selectedConversationId) {
                    ForEach(groupedConversations, id: \.key) { group in
                        Section(header: Text(group.key).font(.system(size: 10, weight: .medium))) {
                            ForEach(group.conversations) { conversation in
                                ConversationRow(conversation: conversation, isSelected: store.selectedConversationId == conversation.id)
                                    .tag(conversation.id)
                                    .contextMenu {
                                        Button(role: .destructive) {
                                            store.deleteConversation(conversation.id)
                                        } label: {
                                            Label("Delete", systemImage: "trash")
                                        }
                                    }
                            }
                        }
                    }
                }
                .listStyle(.sidebar)
            }
        }
        .frame(minWidth: 180, idealWidth: 220, maxWidth: 280)
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

        for conversation in store.conversations {
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
        if !thisWeek.isEmpty { groups.append(ConversationGroup(key: "This Week", conversations: thisWeek)) }
        if !thisMonth.isEmpty { groups.append(ConversationGroup(key: "This Month", conversations: thisMonth)) }
        if !older.isEmpty { groups.append(ConversationGroup(key: "Older", conversations: older)) }

        return groups
    }
}

struct ConversationGroup: Identifiable {
    let key: String
    let conversations: [Conversation]
    var id: String { key }
}

struct ConversationRow: View {
    let conversation: Conversation
    let isSelected: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(conversation.title)
                .font(.system(size: 12, weight: isSelected ? .medium : .regular))
                .lineLimit(1)
                .foregroundColor(isSelected ? .primary : .primary)

            Text(conversation.preview)
                .font(.system(size: 10))
                .foregroundColor(.secondary)
                .lineLimit(1)
        }
        .padding(.vertical, 4)
    }
}
