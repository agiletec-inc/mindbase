import Foundation

/// File System Watcher for AI conversation directories
/// Monitors Claude Code, Cursor, Windsurf, ChatGPT and triggers callback on changes
class ConversationWatcher {
    private var streams: [FileSystemEventStream] = []
    private let callback: (String, String) -> Void
    private var debounceTimers: [String: Timer] = [:]
    private let debounceInterval: TimeInterval = 1.0

    init(onConversationDetected: @escaping (String, String) -> Void) {
        self.callback = onConversationDetected
    }

    func start() {
        let watchPaths = getWatchPaths()

        for (source, path) in watchPaths {
            guard FileManager.default.fileExists(atPath: path) else {
                print("[Watcher] Skip \(source): directory not found (\(path))")
                continue
            }

            let stream = FileSystemEventStream(
                path: path,
                callback: { [weak self] eventPath in
                    self?.handleFileChange(source: source, path: eventPath)
                }
            )

            stream.start()
            streams.append(stream)
            print("[Watcher] Watching \(source): \(path)")
        }

        print("[Watcher] Started watching \(streams.count) directories")
    }

    func stop() {
        for stream in streams {
            stream.stop()
        }
        streams.removeAll()

        for timer in debounceTimers.values {
            timer.invalidate()
        }
        debounceTimers.removeAll()

        print("[Watcher] All watchers stopped")
    }

    private func getWatchPaths() -> [String: String] {
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        return [
            "claude-code": "\(home)/.claude",
            "claude-desktop": "\(home)/Library/Application Support/Claude",
            "cursor": "\(home)/.cursor",
            "windsurf": "\(home)/Library/Application Support/Windsurf",
            "chatgpt": "\(home)/Library/Application Support/ChatGPT"
        ]
    }

    private func handleFileChange(source: String, path: String) {
        // Filter: only JSON/JSONL files
        guard path.hasSuffix(".json") || path.hasSuffix(".jsonl") else {
            return
        }

        // Debounce
        let debounceKey = "\(source):\(path)"
        debounceTimers[debounceKey]?.invalidate()

        debounceTimers[debounceKey] = Timer.scheduledTimer(withTimeInterval: debounceInterval, repeats: false) { [weak self] _ in
            self?.callback(source, path)
            self?.debounceTimers.removeValue(forKey: debounceKey)
        }
    }
}

// MARK: - FSEvents Wrapper
class FileSystemEventStream {
    private let path: String
    private let callback: (String) -> Void
    private var streamRef: FSEventStreamRef?

    init(path: String, callback: @escaping (String) -> Void) {
        self.path = path
        self.callback = callback
    }

    func start() {
        var context = FSEventStreamContext(
            version: 0,
            info: Unmanaged.passUnretained(self).toOpaque(),
            retain: nil,
            release: nil,
            copyDescription: nil
        )

        let paths = [path] as CFArray
        let flags = UInt32(kFSEventStreamCreateFlagFileEvents | kFSEventStreamCreateFlagUseCFTypes)

        streamRef = FSEventStreamCreate(
            kCFAllocatorDefault,
            { (stream, clientInfo, numEvents, eventPaths, eventFlags, eventIds) in
                guard let clientInfo = clientInfo else { return }
                let watcher = Unmanaged<FileSystemEventStream>.fromOpaque(clientInfo).takeUnretainedValue()

                let paths = unsafeBitCast(eventPaths, to: NSArray.self) as! [String]
                for path in paths {
                    watcher.callback(path)
                }
            },
            &context,
            paths,
            FSEventStreamEventId(kFSEventStreamEventIdSinceNow),
            1.0, // latency
            flags
        )

        if let streamRef = streamRef {
            FSEventStreamScheduleWithRunLoop(streamRef, CFRunLoopGetMain(), CFRunLoopMode.defaultMode.rawValue)
            FSEventStreamStart(streamRef)
        }
    }

    func stop() {
        if let streamRef = streamRef {
            FSEventStreamStop(streamRef)
            FSEventStreamInvalidate(streamRef)
            FSEventStreamRelease(streamRef)
            self.streamRef = nil
        }
    }

    deinit {
        stop()
    }
}
