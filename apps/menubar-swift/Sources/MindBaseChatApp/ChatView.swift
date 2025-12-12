import SwiftUI
import MindBaseChatCore

struct ChatView: View {
    @ObservedObject var viewModel: ChatViewModel
    @FocusState private var isInputFocused: Bool
    @State private var inputText = ""

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HeaderView(viewModel: viewModel)

            Divider()

            // Messages
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 0) {
                        ForEach(viewModel.messages) { message in
                            MessageView(message: message)
                                .id(message.id)
                        }

                        // Streaming text
                        if viewModel.isStreaming && !viewModel.streamingText.isEmpty {
                            StreamingMessageView(text: viewModel.streamingText)
                                .id("streaming")
                        }

                        // Typing indicator
                        if viewModel.isStreaming && viewModel.streamingText.isEmpty {
                            TypingIndicator()
                                .id("typing")
                        }
                    }
                    .padding(.vertical, 16)
                }
                .onChange(of: viewModel.messages.count) {
                    scrollToBottom(proxy: proxy)
                }
                .onChange(of: viewModel.streamingText) {
                    scrollToBottom(proxy: proxy, id: "streaming")
                }
            }

            // Error banner
            if let error = viewModel.error {
                ErrorBanner(message: error) {
                    viewModel.error = nil
                }
            }

            Divider()

            // Input area
            InputArea(
                text: $inputText,
                isStreaming: viewModel.isStreaming,
                onSend: sendMessage,
                onStop: { viewModel.stop() }
            )
            .focused($isInputFocused)
        }
        .background(Color(nsColor: .textBackgroundColor))
        .onAppear {
            isInputFocused = true
        }
    }

    private func sendMessage() {
        guard !inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        viewModel.send(inputText)
        inputText = ""
    }

    private func scrollToBottom(proxy: ScrollViewProxy, id: String? = nil) {
        if let stringId = id {
            withAnimation(.easeOut(duration: 0.15)) {
                proxy.scrollTo(stringId, anchor: .bottom)
            }
        } else if let lastMessage = viewModel.messages.last {
            withAnimation(.easeOut(duration: 0.15)) {
                proxy.scrollTo(lastMessage.id, anchor: .bottom)
            }
        }
    }
}

// MARK: - Header

struct HeaderView: View {
    @ObservedObject var viewModel: ChatViewModel

    var body: some View {
        HStack {
            // Model selector
            Menu {
                if viewModel.isLoadingModels {
                    Text("Loading...")
                } else if viewModel.availableModels.isEmpty {
                    Text("No models found")
                    Button("Refresh") {
                        Task { await viewModel.loadModels() }
                    }
                } else {
                    ForEach(viewModel.availableModels, id: \.name) { model in
                        Button {
                            viewModel.selectModel(model)
                        } label: {
                            HStack {
                                Text(model.displayName)
                                if !model.sizeFormatted.isEmpty {
                                    Text(model.sizeFormatted)
                                        .foregroundColor(.secondary)
                                }
                                if model.name == viewModel.selectedModel {
                                    Spacer()
                                    Image(systemName: "checkmark")
                                }
                            }
                        }
                    }

                    Divider()

                    Button {
                        Task { await viewModel.loadModels() }
                    } label: {
                        Label("Refresh Models", systemImage: "arrow.clockwise")
                    }
                }
            } label: {
                HStack(spacing: 4) {
                    Image(systemName: "cpu")
                    Text(viewModel.selectedModel.replacingOccurrences(of: ":latest", with: ""))
                        .lineLimit(1)
                    Image(systemName: "chevron.down")
                        .font(.system(size: 10))
                }
                .font(.system(size: 12))
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(Color.gray.opacity(0.1))
                .cornerRadius(6)
            }
            .buttonStyle(.plain)

            Spacer()

            // Clear button
            Button {
                viewModel.clearChat()
            } label: {
                Image(systemName: "trash")
                    .font(.system(size: 12))
            }
            .buttonStyle(.plain)
            .help("Clear chat (Cmd+Shift+K)")
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(Color(nsColor: .windowBackgroundColor))
    }
}

// MARK: - Message View

struct MessageView: View {
    let message: ChatMessage

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            // Avatar
            ZStack {
                Circle()
                    .fill(message.role == .user ? Color.blue : Color.purple)
                    .frame(width: 28, height: 28)

                Image(systemName: message.role == .user ? "person.fill" : "brain")
                    .font(.system(size: 12))
                    .foregroundColor(.white)
            }

            // Content
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(message.role == .user ? "You" : "MindBase")
                        .font(.system(size: 12, weight: .semibold))

                    if message.ragContextCount > 0 {
                        Text("RAG \(message.ragContextCount)")
                            .font(.system(size: 9))
                            .padding(.horizontal, 4)
                            .padding(.vertical, 2)
                            .background(Color.green.opacity(0.2))
                            .cornerRadius(4)
                    }

                    Spacer()

                    Text(message.timestamp, style: .time)
                        .font(.system(size: 10))
                        .foregroundColor(.secondary)
                }

                // Markdown content with code blocks
                MarkdownContentView(content: message.content)
            }
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 10)
        .background(message.role == .assistant ? Color.gray.opacity(0.03) : Color.clear)
    }
}

// MARK: - Markdown Content View

struct MarkdownContentView: View {
    let content: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            ForEach(Array(parseContent().enumerated()), id: \.offset) { _, block in
                switch block {
                case .text(let text):
                    Text(text)
                        .font(.system(size: 13))
                        .textSelection(.enabled)
                        .lineSpacing(4)
                case .code(let code, let language):
                    CodeBlockView(code: code, language: language)
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
            // Text before code block
            if match.range.location > lastEnd {
                let textRange = NSRange(location: lastEnd, length: match.range.location - lastEnd)
                let text = nsContent.substring(with: textRange).trimmingCharacters(in: .whitespacesAndNewlines)
                if !text.isEmpty {
                    blocks.append(.text(text))
                }
            }

            // Code block
            let languageRange = match.range(at: 1)
            let codeRange = match.range(at: 2)

            let language = languageRange.location != NSNotFound ? nsContent.substring(with: languageRange) : ""
            let code = codeRange.location != NSNotFound ? nsContent.substring(with: codeRange).trimmingCharacters(in: .newlines) : ""

            blocks.append(.code(code, language))
            lastEnd = match.range.location + match.range.length
        }

        // Remaining text
        if lastEnd < nsContent.length {
            let text = nsContent.substring(from: lastEnd).trimmingCharacters(in: .whitespacesAndNewlines)
            if !text.isEmpty {
                blocks.append(.text(text))
            }
        }

        return blocks.isEmpty ? [.text(content)] : blocks
    }

    enum ContentBlock {
        case text(String)
        case code(String, String) // code, language
    }
}

// MARK: - Code Block View

struct CodeBlockView: View {
    let code: String
    let language: String
    @State private var copied = false

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header with language and copy button
            HStack {
                Text(language.isEmpty ? "code" : language)
                    .font(.system(size: 10, weight: .medium))
                    .foregroundColor(.secondary)

                Spacer()

                Button {
                    copyToClipboard()
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: copied ? "checkmark" : "doc.on.doc")
                            .font(.system(size: 10))
                        Text(copied ? "Copied!" : "Copy")
                            .font(.system(size: 10))
                    }
                    .foregroundColor(copied ? .green : .secondary)
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(Color.black.opacity(0.3))

            // Code content
            ScrollView(.horizontal, showsIndicators: false) {
                Text(code)
                    .font(.system(size: 12, design: .monospaced))
                    .foregroundColor(.white)
                    .textSelection(.enabled)
                    .padding(12)
            }
        }
        .background(Color(nsColor: NSColor(red: 0.1, green: 0.1, blue: 0.12, alpha: 1)))
        .cornerRadius(8)
    }

    private func copyToClipboard() {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(code, forType: .string)
        copied = true

        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
            copied = false
        }
    }
}

// MARK: - Streaming Message

struct StreamingMessageView: View {
    let text: String

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            ZStack {
                Circle()
                    .fill(Color.purple)
                    .frame(width: 28, height: 28)

                Image(systemName: "brain")
                    .font(.system(size: 12))
                    .foregroundColor(.white)
            }

            VStack(alignment: .leading, spacing: 4) {
                Text("MindBase")
                    .font(.system(size: 12, weight: .semibold))

                Text(text + "▋")
                    .font(.system(size: 13))
                    .lineSpacing(4)
            }

            Spacer()
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 10)
        .background(Color.gray.opacity(0.03))
    }
}

// MARK: - Typing Indicator

struct TypingIndicator: View {
    @State private var dotCount = 0

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            ZStack {
                Circle()
                    .fill(Color.purple)
                    .frame(width: 28, height: 28)

                Image(systemName: "brain")
                    .font(.system(size: 12))
                    .foregroundColor(.white)
            }

            HStack(spacing: 4) {
                ForEach(0..<3, id: \.self) { index in
                    Circle()
                        .fill(Color.purple)
                        .frame(width: 6, height: 6)
                        .opacity(dotCount == index ? 1 : 0.3)
                }
            }
            .padding(.top, 8)

            Spacer()
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 10)
        .background(Color.gray.opacity(0.03))
        .task {
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 300_000_000)
                dotCount = (dotCount + 1) % 3
            }
        }
    }
}

// MARK: - Input Area

struct InputArea: View {
    @Binding var text: String
    let isStreaming: Bool
    let onSend: () -> Void
    let onStop: () -> Void

    var body: some View {
        HStack(alignment: .bottom, spacing: 10) {
            // Text input
            TextField("Message MindBase...", text: $text, axis: .vertical)
                .textFieldStyle(.plain)
                .font(.system(size: 13))
                .lineLimit(1...8)
                .padding(10)
                .background(Color(nsColor: .controlBackgroundColor))
                .cornerRadius(10)
                .onSubmit {
                    if !NSEvent.modifierFlags.contains(.shift) && !isStreaming {
                        onSend()
                    }
                }

            // Send / Stop button
            if isStreaming {
                Button(action: onStop) {
                    Image(systemName: "stop.circle.fill")
                        .font(.system(size: 26))
                        .foregroundColor(.red)
                }
                .buttonStyle(.plain)
                .help("Stop (Cmd+.)")
            } else {
                Button(action: onSend) {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.system(size: 26))
                        .foregroundColor(canSend ? .accentColor : .gray)
                }
                .buttonStyle(.plain)
                .disabled(!canSend)
                .help("Send (Return)")
            }
        }
        .padding(12)
        .background(Color(nsColor: .windowBackgroundColor))
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
                .font(.system(size: 12))
                .lineLimit(2)

            Spacer()

            Button(action: onDismiss) {
                Image(systemName: "xmark")
                    .font(.system(size: 10))
            }
            .buttonStyle(.plain)
        }
        .padding(10)
        .background(Color.orange.opacity(0.1))
    }
}
