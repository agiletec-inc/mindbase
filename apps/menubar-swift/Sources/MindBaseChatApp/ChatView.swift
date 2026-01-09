import SwiftUI
import MindBaseChatCore

// ChatGPT-style chat view
struct ChatView: View {
    @ObservedObject var viewModel: ChatViewModel
    @FocusState private var isInputFocused: Bool
    @State private var inputText = ""
    @State private var showSettings = false

    private let maxContentWidth: CGFloat = 768
    private let backgroundColor = Color(red: 0.13, green: 0.13, blue: 0.14)

    var body: some View {
        VStack(spacing: 0) {
            // Minimal header
            ChatHeader(viewModel: viewModel, showSettings: $showSettings)

            // Messages area
            ScrollViewReader { proxy in
                ScrollView {
                    VStack(spacing: 0) {
                        if viewModel.messages.isEmpty && !viewModel.isStreaming {
                            EmptyStateView()
                        } else {
                            ForEach(viewModel.messages) { message in
                                ChatMessageRow(message: message) {
                                    viewModel.deleteMessage(message.id)
                                }
                                .id(message.id)
                            }

                            if viewModel.isStreaming {
                                if viewModel.streamingText.isEmpty {
                                    ThinkingIndicator()
                                        .id("thinking")
                                } else {
                                    StreamingRow(text: viewModel.streamingText)
                                        .id("streaming")
                                }
                            }
                        }
                    }
                    .frame(maxWidth: maxContentWidth)
                    .frame(maxWidth: .infinity)
                    .padding(.bottom, 100)
                }
                .onChange(of: viewModel.messages.count) {
                    scrollToBottom(proxy: proxy)
                }
                .onChange(of: viewModel.streamingText) {
                    if viewModel.isStreaming {
                        withAnimation(.easeOut(duration: 0.1)) {
                            proxy.scrollTo("streaming", anchor: .bottom)
                        }
                    }
                }
            }

            // Error banner
            if let error = viewModel.error {
                ErrorBanner(message: error) {
                    viewModel.error = nil
                }
            }

            // Input area (ChatGPT style - centered, rounded)
            ChatInputArea(
                text: $inputText,
                isStreaming: viewModel.isStreaming,
                onSend: sendMessage,
                onStop: { viewModel.stop() }
            )
            .focused($isInputFocused)
        }
        .background(backgroundColor)
        .onAppear {
            isInputFocused = true
        }
        .sheet(isPresented: $showSettings) {
            SettingsView(viewModel: viewModel)
        }
    }

    private func sendMessage() {
        guard !inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        viewModel.send(inputText)
        inputText = ""
    }

    private func scrollToBottom(proxy: ScrollViewProxy) {
        if let lastMessage = viewModel.messages.last {
            withAnimation(.easeOut(duration: 0.15)) {
                proxy.scrollTo(lastMessage.id, anchor: .bottom)
            }
        }
    }
}

// MARK: - Header (Minimal)

struct ChatHeader: View {
    @ObservedObject var viewModel: ChatViewModel
    @Binding var showSettings: Bool

    var body: some View {
        HStack {
            // Model selector (subtle)
            Menu {
                ForEach(viewModel.availableModels, id: \.name) { model in
                    Button {
                        viewModel.selectModel(model)
                    } label: {
                        HStack {
                            Text(model.displayName)
                            if model.name == viewModel.selectedModel {
                                Image(systemName: "checkmark")
                            }
                        }
                    }
                }
                Divider()
                Button("Refresh Models") {
                    Task { await viewModel.loadModels() }
                }
            } label: {
                HStack(spacing: 6) {
                    Text(viewModel.selectedModel.replacingOccurrences(of: ":latest", with: ""))
                        .font(.system(size: 14, weight: .medium))
                    Image(systemName: "chevron.down")
                        .font(.system(size: 10, weight: .medium))
                }
                .foregroundColor(.white.opacity(0.9))
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(Color.white.opacity(0.05))
                .cornerRadius(8)
            }
            .buttonStyle(.plain)

            Spacer()

            // Settings
            Button {
                showSettings = true
            } label: {
                Image(systemName: "gearshape")
                    .font(.system(size: 14))
                    .foregroundColor(.white.opacity(0.6))
            }
            .buttonStyle(.plain)
            .padding(8)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
    }
}

// MARK: - Empty State

struct EmptyStateView: View {
    var body: some View {
        VStack(spacing: 16) {
            Spacer()
            Image(systemName: "brain")
                .font(.system(size: 48))
                .foregroundColor(.white.opacity(0.2))
            Text("How can I help you today?")
                .font(.system(size: 24, weight: .medium))
                .foregroundColor(.white.opacity(0.8))
            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(.top, 100)
    }
}

// MARK: - Message Row (ChatGPT style)

struct ChatMessageRow: View {
    let message: ChatMessage
    let onDelete: () -> Void
    @State private var isHovering = false
    @State private var copied = false

    var body: some View {
        HStack(alignment: .top, spacing: 16) {
            // Avatar
            Circle()
                .fill(message.role == .user ? Color.blue : Color.purple.opacity(0.8))
                .frame(width: 32, height: 32)
                .overlay(
                    Image(systemName: message.role == .user ? "person.fill" : "sparkles")
                        .font(.system(size: 14))
                        .foregroundColor(.white)
                )

            // Content
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text(message.role == .user ? "You" : "MindBase")
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundColor(.white)

                    if message.ragContextCount > 0 {
                        Text("·")
                            .foregroundColor(.white.opacity(0.4))
                        Text("\(message.ragContextCount) sources")
                            .font(.system(size: 12))
                            .foregroundColor(.green.opacity(0.8))
                    }

                    Spacer()

                    if isHovering {
                        HStack(spacing: 8) {
                            Button {
                                copyMessage()
                            } label: {
                                Image(systemName: copied ? "checkmark" : "doc.on.doc")
                                    .font(.system(size: 12))
                                    .foregroundColor(copied ? .green : .white.opacity(0.5))
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }

                MarkdownText(content: message.content)
            }
        }
        .padding(.horizontal, 24)
        .padding(.vertical, 16)
        .background(message.role == .assistant ? Color.white.opacity(0.02) : Color.clear)
        .onHover { isHovering = $0 }
        .contextMenu {
            Button("Copy") { copyMessage() }
            Divider()
            Button("Delete", role: .destructive, action: onDelete)
        }
    }

    private func copyMessage() {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(message.content, forType: .string)
        copied = true
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) { copied = false }
    }
}

// MARK: - Streaming Row

struct StreamingRow: View {
    let text: String

    var body: some View {
        HStack(alignment: .top, spacing: 16) {
            Circle()
                .fill(Color.purple.opacity(0.8))
                .frame(width: 32, height: 32)
                .overlay(
                    Image(systemName: "sparkles")
                        .font(.system(size: 14))
                        .foregroundColor(.white)
                )

            VStack(alignment: .leading, spacing: 8) {
                Text("MindBase")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundColor(.white)

                HStack(alignment: .bottom, spacing: 0) {
                    Text(text)
                        .font(.system(size: 15))
                        .foregroundColor(.white.opacity(0.9))
                        .lineSpacing(6)
                    Text("▋")
                        .font(.system(size: 15))
                        .foregroundColor(.white.opacity(0.5))
                }
            }

            Spacer()
        }
        .padding(.horizontal, 24)
        .padding(.vertical, 16)
        .background(Color.white.opacity(0.02))
    }
}

// MARK: - Thinking Indicator

struct ThinkingIndicator: View {
    @State private var opacity: Double = 0.3

    var body: some View {
        HStack(alignment: .top, spacing: 16) {
            Circle()
                .fill(Color.purple.opacity(0.8))
                .frame(width: 32, height: 32)
                .overlay(
                    Image(systemName: "sparkles")
                        .font(.system(size: 14))
                        .foregroundColor(.white)
                )

            HStack(spacing: 4) {
                ForEach(0..<3, id: \.self) { i in
                    Circle()
                        .fill(Color.white.opacity(opacity))
                        .frame(width: 8, height: 8)
                        .animation(.easeInOut(duration: 0.6).repeatForever().delay(Double(i) * 0.2), value: opacity)
                }
            }
            .padding(.top, 8)
            .onAppear { opacity = 0.8 }

            Spacer()
        }
        .padding(.horizontal, 24)
        .padding(.vertical, 16)
        .background(Color.white.opacity(0.02))
    }
}

// MARK: - Markdown Text

struct MarkdownText: View {
    let content: String

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            ForEach(Array(parseContent().enumerated()), id: \.offset) { _, block in
                switch block {
                case .text(let text):
                    Text(text)
                        .font(.system(size: 15))
                        .foregroundColor(.white.opacity(0.9))
                        .lineSpacing(6)
                        .textSelection(.enabled)
                case .code(let code, let language):
                    CodeBlock(code: code, language: language)
                }
            }
        }
    }

    private func parseContent() -> [ContentBlock] {
        var blocks: [ContentBlock] = []
        let pattern = "```(\\w*)\\n([\\s\\S]*?)```"

        guard let regex = try? NSRegularExpression(pattern: pattern, options: []) else {
            return [.text(content)]
        }

        let nsContent = content as NSString
        var lastEnd = 0
        let matches = regex.matches(in: content, options: [], range: NSRange(location: 0, length: nsContent.length))

        for match in matches {
            if match.range.location > lastEnd {
                let textRange = NSRange(location: lastEnd, length: match.range.location - lastEnd)
                let text = nsContent.substring(with: textRange).trimmingCharacters(in: .whitespacesAndNewlines)
                if !text.isEmpty { blocks.append(.text(text)) }
            }

            let languageRange = match.range(at: 1)
            let codeRange = match.range(at: 2)
            let language = languageRange.location != NSNotFound ? nsContent.substring(with: languageRange) : ""
            let code = codeRange.location != NSNotFound ? nsContent.substring(with: codeRange).trimmingCharacters(in: .newlines) : ""
            blocks.append(.code(code, language))
            lastEnd = match.range.location + match.range.length
        }

        if lastEnd < nsContent.length {
            let text = nsContent.substring(from: lastEnd).trimmingCharacters(in: .whitespacesAndNewlines)
            if !text.isEmpty { blocks.append(.text(text)) }
        }

        return blocks.isEmpty ? [.text(content)] : blocks
    }

    enum ContentBlock {
        case text(String)
        case code(String, String)
    }
}

// MARK: - Code Block

struct CodeBlock: View {
    let code: String
    let language: String
    @State private var copied = false

    private let codeBackground = Color(red: 0.08, green: 0.08, blue: 0.08)

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header
            HStack {
                Text(language.isEmpty ? "code" : language)
                    .font(.system(size: 12, weight: .medium))
                    .foregroundColor(.white.opacity(0.5))
                Spacer()
                Button {
                    NSPasteboard.general.clearContents()
                    NSPasteboard.general.setString(code, forType: .string)
                    copied = true
                    DispatchQueue.main.asyncAfter(deadline: .now() + 2) { copied = false }
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: copied ? "checkmark" : "doc.on.doc")
                        Text(copied ? "Copied!" : "Copy")
                    }
                    .font(.system(size: 11))
                    .foregroundColor(copied ? .green : .white.opacity(0.5))
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(Color.black.opacity(0.3))

            // Code
            ScrollView(.horizontal, showsIndicators: false) {
                Text(code)
                    .font(.system(size: 13, design: .monospaced))
                    .foregroundColor(.white.opacity(0.9))
                    .textSelection(.enabled)
                    .padding(12)
            }
        }
        .background(codeBackground)
        .cornerRadius(8)
    }
}

// MARK: - Input Area (ChatGPT style)

struct ChatInputArea: View {
    @Binding var text: String
    let isStreaming: Bool
    let onSend: () -> Void
    let onStop: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            HStack(alignment: .bottom, spacing: 12) {
                // Text input
                TextField("Message MindBase...", text: $text, axis: .vertical)
                    .textFieldStyle(.plain)
                    .font(.system(size: 15))
                    .foregroundColor(.white)
                    .lineLimit(1...10)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 12)
                    .onSubmit {
                        if !isStreaming && !NSEvent.modifierFlags.contains(.shift) {
                            onSend()
                        }
                    }

                // Send/Stop button
                Button(action: isStreaming ? onStop : onSend) {
                    Image(systemName: isStreaming ? "stop.fill" : "arrow.up")
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundColor(isStreaming ? .white : (canSend ? .white : .white.opacity(0.3)))
                        .frame(width: 32, height: 32)
                        .background(isStreaming ? Color.red : (canSend ? Color.white.opacity(0.15) : Color.white.opacity(0.05)))
                        .clipShape(Circle())
                }
                .buttonStyle(.plain)
                .disabled(!isStreaming && !canSend)
                .padding(.trailing, 8)
                .padding(.bottom, 8)
            }
            .background(Color.white.opacity(0.08))
            .cornerRadius(24)
            .overlay(
                RoundedRectangle(cornerRadius: 24)
                    .stroke(Color.white.opacity(0.1), lineWidth: 1)
            )
            .padding(.horizontal, 16)
            .padding(.bottom, 16)

            // Hint text
            Text("MindBase may produce inaccurate information.")
                .font(.system(size: 11))
                .foregroundColor(.white.opacity(0.3))
                .padding(.bottom, 8)
        }
        .background(Color(red: 0.13, green: 0.13, blue: 0.14))
    }

    private var canSend: Bool {
        !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }
}

// MARK: - Error Banner

struct ErrorBanner: View {
    let message: String
    let onDismiss: () -> Void

    var body: some View {
        HStack {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundColor(.orange)
            Text(message)
                .font(.system(size: 13))
                .foregroundColor(.white)
            Spacer()
            Button(action: onDismiss) {
                Image(systemName: "xmark")
                    .font(.system(size: 11))
                    .foregroundColor(.white.opacity(0.6))
            }
            .buttonStyle(.plain)
        }
        .padding(12)
        .background(Color.orange.opacity(0.15))
        .cornerRadius(8)
        .padding(.horizontal, 16)
    }
}
