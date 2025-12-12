import XCTest
@testable import MindBaseChatCore

final class OllamaClientTests: XCTestCase {

    // MARK: - Model Tests

    func testOllamaModelDisplayName() {
        let model1 = OllamaModel(name: "qwen2.5:3b", modifiedAt: nil, size: nil)
        XCTAssertEqual(model1.displayName, "qwen2.5:3b")

        let model2 = OllamaModel(name: "llama3:latest", modifiedAt: nil, size: nil)
        XCTAssertEqual(model2.displayName, "llama3")
    }

    func testOllamaModelSizeFormatted() {
        let model1 = OllamaModel(name: "test", modifiedAt: nil, size: 3_500_000_000)
        XCTAssertEqual(model1.sizeFormatted, "3.5GB")

        let model2 = OllamaModel(name: "test", modifiedAt: nil, size: 500_000_000)
        XCTAssertEqual(model2.sizeFormatted, "0.5GB")

        let model3 = OllamaModel(name: "test", modifiedAt: nil, size: nil)
        XCTAssertEqual(model3.sizeFormatted, "")
    }

    // MARK: - Chat Message Tests

    func testOllamaChatMessageDictionary() {
        let message = OllamaChatMessage(role: "user", content: "Hello")
        let dict = message.dictionary

        XCTAssertEqual(dict["role"], "user")
        XCTAssertEqual(dict["content"], "Hello")
    }

    // MARK: - Options Tests

    func testOllamaOptionsDefaults() {
        let options = OllamaOptions()

        XCTAssertEqual(options.temperature, 0.7)
        XCTAssertEqual(options.topP, 0.9)
        XCTAssertEqual(options.topK, 40)
        XCTAssertEqual(options.numPredict, 2048)
    }

    func testOllamaOptionsCustom() {
        let options = OllamaOptions(temperature: 0.5, topP: 0.8, topK: 30, numPredict: 1024)

        XCTAssertEqual(options.temperature, 0.5)
        XCTAssertEqual(options.topP, 0.8)
        XCTAssertEqual(options.topK, 30)
        XCTAssertEqual(options.numPredict, 1024)
    }

    func testOllamaOptionsDictionary() {
        let options = OllamaOptions(temperature: 0.5, topP: 0.8, topK: 30, numPredict: 1024)
        let dict = options.dictionary

        XCTAssertEqual(dict["temperature"] as? Double, 0.5)
        XCTAssertEqual(dict["top_p"] as? Double, 0.8)
        XCTAssertEqual(dict["top_k"] as? Int, 30)
        XCTAssertEqual(dict["num_predict"] as? Int, 1024)
    }

    // MARK: - Pull Progress Tests

    func testOllamaPullProgressCalculation() {
        let progress1 = OllamaPullProgress(status: "downloading", digest: "abc", total: 1000, completed: 500)
        XCTAssertEqual(progress1.progress, 0.5)

        let progress2 = OllamaPullProgress(status: "downloading", digest: "abc", total: 1000, completed: 1000)
        XCTAssertEqual(progress2.progress, 1.0)

        let progress3 = OllamaPullProgress(status: "downloading", digest: nil, total: nil, completed: nil)
        XCTAssertEqual(progress3.progress, 0.0)

        let progress4 = OllamaPullProgress(status: "downloading", digest: "abc", total: 0, completed: 0)
        XCTAssertEqual(progress4.progress, 0.0)
    }

    // MARK: - Error Tests

    func testOllamaErrorDescriptions() {
        XCTAssertEqual(OllamaError.invalidResponse.errorDescription, "Invalid response from Ollama")
        XCTAssertEqual(OllamaError.httpError(404).errorDescription, "HTTP error: 404")
        XCTAssertEqual(OllamaError.notReachable.errorDescription, "Ollama is not running. Please start Ollama first.")
        XCTAssertEqual(OllamaError.modelNotFound("test").errorDescription, "Model 'test' not found. Pull it first.")
    }

    // MARK: - Chat Chunk Tests

    func testOllamaChatChunkDecoding() throws {
        let json = """
        {"model": "qwen2.5:3b", "message": {"role": "assistant", "content": "Hello"}, "done": false}
        """
        let data = json.data(using: .utf8)!
        let chunk = try JSONDecoder().decode(OllamaChatChunk.self, from: data)

        XCTAssertEqual(chunk.model, "qwen2.5:3b")
        XCTAssertEqual(chunk.message?.role, "assistant")
        XCTAssertEqual(chunk.message?.content, "Hello")
        XCTAssertFalse(chunk.done)
    }

    func testOllamaChatChunkDecodingDone() throws {
        let json = """
        {"model": "qwen2.5:3b", "done": true}
        """
        let data = json.data(using: .utf8)!
        let chunk = try JSONDecoder().decode(OllamaChatChunk.self, from: data)

        XCTAssertTrue(chunk.done)
        XCTAssertNil(chunk.message)
    }
}
