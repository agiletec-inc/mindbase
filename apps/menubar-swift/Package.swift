// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "MindBase",
    platforms: [
        .macOS(.v15)
    ],
    dependencies: [],
    targets: [
        // Menubar app
        .executableTarget(
            name: "MindBaseMenubar",
            dependencies: [],
            path: "Sources/MindBaseMenubar"
        ),
        // Chat app core library (testable)
        .target(
            name: "MindBaseChatCore",
            dependencies: [],
            path: "Sources/MindBaseChatCore"
        ),
        // Chat app executable
        .executableTarget(
            name: "MindBaseChat",
            dependencies: ["MindBaseChatCore"],
            path: "Sources/MindBaseChatApp"
        ),
        // Tests
        .testTarget(
            name: "MindBaseChatTests",
            dependencies: ["MindBaseChatCore"],
            path: "Tests/MindBaseChatTests"
        )
    ]
)
