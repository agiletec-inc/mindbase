// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "MindBaseMenubar",
    platforms: [
        .macOS(.v15)
    ],
    dependencies: [],
    targets: [
        .executableTarget(
            name: "MindBaseMenubar",
            dependencies: [],
            swiftSettings: [
                .enableUpcomingFeature("BareSlashRegexLiterals")
            ]
        )
    ]
)
