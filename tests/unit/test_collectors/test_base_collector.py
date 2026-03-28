"""
Unit tests for BaseCollector.
"""
import pytest
from datetime import datetime, timezone
from collectors.base_collector import BaseCollector, Conversation, Message


class TestMessage:
    """Test Message dataclass."""

    def test_message_creation(self):
        """Test message creation with required fields."""
        msg = Message(
            role="user",
            content="Hello, world!",
            timestamp=datetime.now(timezone.utc),
        )
        assert msg.role == "user"
        assert msg.content == "Hello, world!"
        assert msg.message_id is not None  # Auto-generated

    def test_message_id_generation(self):
        """Test message ID is generated from content hash."""
        fixed_ts = datetime(2025, 1, 1, tzinfo=timezone.utc)
        msg1 = Message(
            role="user",
            content="Same content",
            timestamp=fixed_ts,
        )
        msg2 = Message(
            role="user",
            content="Same content",
            timestamp=fixed_ts,
        )
        assert msg1.message_id == msg2.message_id  # Same content+timestamp = same ID


class TestConversation:
    """Test Conversation dataclass."""

    def test_conversation_creation(self, sample_conversation_data):
        """Test conversation creation from data."""
        conv = Conversation(**sample_conversation_data)
        assert conv.source == "claude-code"
        assert conv.title == "Test Conversation"
        assert len(conv.messages) == 2

    def test_get_message_count(self, sample_conversation_data):
        """Test message count helper."""
        conv = Conversation(**sample_conversation_data)
        assert conv.get_message_count() == 2

    def test_get_word_count(self, sample_conversation_data):
        """Test word count helper."""
        conv = Conversation(**sample_conversation_data)
        word_count = conv.get_word_count()
        assert word_count > 0  # Should count words in messages


class TestBaseCollector:
    """Test BaseCollector abstract class."""

    def test_cannot_instantiate_directly(self):
        """Test that BaseCollector cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseCollector()

    def test_validate_conversation(self, sample_conversation_data):
        """Test conversation validation logic."""
        # Create a concrete implementation for testing
        class ConcreteCollector(BaseCollector):
            def get_data_paths(self):
                return []

            def collect(self):
                return []

        collector = ConcreteCollector(source_name="test")
        conv = Conversation(**sample_conversation_data)

        # Should validate successfully
        assert collector.validate_conversation(conv) is True

    def test_validate_conversation_missing_fields(self):
        """Test validation fails with missing required fields."""

        class ConcreteCollector(BaseCollector):
            def get_data_paths(self):
                return []

            def collect(self):
                return []

        collector = ConcreteCollector(source_name="test")

        # Empty messages should fail validation
        invalid_conv = Conversation(
            id="conv_invalid",
            source="test",
            title="",
            messages=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        assert collector.validate_conversation(invalid_conv) is False
