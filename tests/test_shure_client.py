"""Tests for the Shure TCP client protocol parsing."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.shure_wireless.shure_client import (
    ChannelState,
    ReceiverState,
    ShureClient,
)


class TestChannelState:
    """Test ChannelState defaults."""

    def test_defaults(self):
        state = ChannelState()
        assert state.name == ""
        assert state.frequency == ""
        assert state.audio_level == -120
        assert state.rf_level == -120
        assert state.battery_bars is None
        assert state.battery_charge is None
        assert state.battery_runtime is None


class TestReceiverState:
    """Test ReceiverState defaults."""

    def test_defaults(self):
        state = ReceiverState()
        assert state.device_id == ""
        assert state.firmware_version == ""
        assert state.model == ""


class TestShureClientInit:
    """Test ShureClient initialization."""

    def test_default_channels(self):
        client = ShureClient("192.168.1.1")
        assert client.host == "192.168.1.1"
        assert client.port == 2202
        assert client.num_channels == 4
        assert len(client.channels) == 4
        assert set(client.channels.keys()) == {1, 2, 3, 4}

    def test_custom_channels(self):
        client = ShureClient("10.0.0.1", 3333, num_channels=2)
        assert client.port == 3333
        assert len(client.channels) == 2
        assert set(client.channels.keys()) == {1, 2}

    def test_not_connected_initially(self):
        client = ShureClient("192.168.1.1")
        assert client.connected is False


class TestProtocolParsing:
    """Test the Shure string protocol parsing."""

    def setup_method(self):
        self.client = ShureClient("192.168.1.1", num_channels=2)
        self.callback = MagicMock()
        self.client.register_callback(self.callback)

    def test_process_receiver_fw_ver(self):
        self.client._process_line("REP FW_VER {1.2.3}")
        assert self.client.receiver.firmware_version == "1.2.3"

    def test_process_receiver_device_id(self):
        self.client._process_line("REP DEVICE_ID {SLXD4-001}")
        assert self.client.receiver.device_id == "SLXD4-001"

    def test_process_receiver_model(self):
        self.client._process_line("REP MODEL SLXD4")
        assert self.client.receiver.model == "SLXD4"

    def test_process_receiver_rf_band(self):
        self.client._process_line("REP RF_BAND G58")
        assert self.client.receiver.rf_band == "G58"

    def test_process_receiver_encryption(self):
        self.client._process_line("REP ENCRYPTION OFF")
        assert self.client.receiver.encryption == "OFF"

    def test_process_receiver_lock_status(self):
        self.client._process_line("REP LOCK_STATUS LOCKED")
        assert self.client.receiver.lock_status == "LOCKED"

    def test_process_channel_name(self):
        self.client._process_line("REP 1 CHAN_NAME {Mic 1}")
        assert self.client.channels[1].name == "Mic 1"

    def test_process_channel_frequency(self):
        self.client._process_line("REP 1 FREQUENCY 470125")
        assert self.client.channels[1].frequency == "470.125"

    def test_process_channel_audio_gain(self):
        self.client._process_line("REP 1 AUDIO_GAIN 30")
        assert self.client.channels[1].audio_gain == 12  # 30 - 18

    def test_process_channel_audio_mute(self):
        self.client._process_line("REP 1 AUDIO_MUTE ON")
        assert self.client.channels[1].audio_mute == "ON"

    def test_process_channel_tx_type(self):
        self.client._process_line("REP 1 TX_TYPE SLXD1")
        assert self.client.channels[1].tx_model == "SLXD1"

    def test_process_channel_tx_model(self):
        self.client._process_line("REP 1 TX_MODEL SLXD2")
        assert self.client.channels[1].tx_model == "SLXD2"

    def test_process_channel_tx_device_id(self):
        self.client._process_line("REP 1 TX_DEVICE_ID {TX-ABC}")
        assert self.client.channels[1].tx_device_id == "TX-ABC"

    def test_process_battery_bars(self):
        self.client._process_line("REP 1 BATT_BARS 4")
        assert self.client.channels[1].battery_bars == 4

    def test_process_battery_bars_unknown(self):
        self.client._process_line("REP 1 BATT_BARS 255")
        assert self.client.channels[1].battery_bars is None

    def test_process_battery_charge(self):
        self.client._process_line("REP 1 BATT_CHARGE 80")
        assert self.client.channels[1].battery_charge == 80

    def test_process_battery_charge_unknown(self):
        self.client._process_line("REP 1 BATT_CHARGE 255")
        assert self.client.channels[1].battery_charge is None

    def test_process_battery_runtime(self):
        self.client._process_line("REP 1 BATT_RUN_TIME 180")
        assert self.client.channels[1].battery_runtime == 180

    def test_process_battery_runtime_unknown(self):
        self.client._process_line("REP 1 BATT_RUN_TIME 65535")
        assert self.client.channels[1].battery_runtime is None

    def test_process_tx_batt_mins(self):
        self.client._process_line("REP 1 TX_BATT_MINS 90")
        assert self.client.channels[1].battery_runtime == 90

    def test_process_battery_type(self):
        self.client._process_line("REP 1 BATT_TYPE LITHIUM_ION")
        assert self.client.channels[1].battery_type == "LITHIUM_ION"

    def test_process_battery_health(self):
        self.client._process_line("REP 1 BATT_HEALTH 95")
        assert self.client.channels[1].battery_health == 95

    def test_process_battery_health_unknown(self):
        self.client._process_line("REP 1 BATT_HEALTH 255")
        assert self.client.channels[1].battery_health is None

    def test_process_battery_cycle(self):
        self.client._process_line("REP 1 BATT_CYCLE 50")
        assert self.client.channels[1].battery_cycle == 50

    def test_process_battery_cycle_unknown(self):
        self.client._process_line("REP 1 BATT_CYCLE 65535")
        assert self.client.channels[1].battery_cycle is None

    def test_process_battery_temp(self):
        self.client._process_line("REP 1 BATT_TEMP_C 5")
        assert self.client.channels[1].battery_temp_c == 45  # 5 + 40

    def test_process_battery_temp_unknown(self):
        self.client._process_line("REP 1 BATT_TEMP_C 255")
        assert self.client.channels[1].battery_temp_c is None

    def test_process_interference_none(self):
        self.client._process_line("REP 1 RF_INT_DET NONE")
        assert self.client.channels[1].interference_status == "NONE"

    def test_process_interference_critical(self):
        self.client._process_line("REP 1 RF_INT_DET CRITICAL")
        assert self.client.channels[1].interference_status == "DETECTED"

    def test_process_interference_status_key(self):
        self.client._process_line("REP 1 INTERFERENCE_STATUS CRITICAL")
        assert self.client.channels[1].interference_status == "DETECTED"

    def test_process_encryption_channel(self):
        self.client._process_line("REP 1 ENCRYPTION OFF")
        assert self.client.channels[1].encryption_status == "OK"

    def test_process_encryption_channel_on(self):
        self.client._process_line("REP 1 ENCRYPTION ON")
        assert self.client.channels[1].encryption_status == "ON"

    def test_process_mute_status_on(self):
        """MUTE_STATUS ON means mute is off (active transmitting)."""
        self.client._process_line("REP 1 MUTE_STATUS ON")
        assert self.client.channels[1].tx_mute_status == "OFF"

    def test_process_mute_status_mute(self):
        """MUTE_STATUS MUTE means mute is on."""
        self.client._process_line("REP 1 MUTE_STATUS MUTE")
        assert self.client.channels[1].tx_mute_status == "ON"

    def test_process_mute_mode_status(self):
        self.client._process_line("REP 1 MUTE_MODE_STATUS ON")
        assert self.client.channels[1].tx_mute_status == "OFF"

    def test_unknown_channel_ignored(self):
        """Updates to non-existent channels should be silently ignored."""
        self.client._process_line("REP 9 CHAN_NAME {Ghost}")
        # Should not raise

    def test_callback_called(self):
        self.client._process_line("REP 1 CHAN_NAME {Test}")
        self.callback.assert_called()

    def test_callback_called_on_receiver_update(self):
        self.client._process_line("REP MODEL SLXD4")
        self.callback.assert_called()

    def test_callback_error_does_not_propagate(self):
        self.callback.side_effect = RuntimeError("boom")
        # Should not raise
        self.client._process_line("REP 1 CHAN_NAME {Test}")

    def test_short_line_ignored(self):
        """Lines with fewer than 2 parts should be ignored."""
        self.client._process_line("REP")
        self.callback.assert_not_called()

    def test_short_rep_ignored(self):
        self.client._process_line("REP 1")
        self.callback.assert_not_called()


class TestSampleParsing:
    """Test SAMPLE message parsing."""

    def setup_method(self):
        self.client = ShureClient("192.168.1.1", num_channels=2)
        self.callback = MagicMock()
        self.client.register_callback(self.callback)

    def test_sample_parsing(self):
        # Format after _process_line splits: parts = [ch, ALL, ?, peak, rms, rf]
        # Code uses parts[3]=peak, parts[4]=rms, parts[5]=rf
        self.client._process_line("SAMPLE 1 ALL 000 095 080 070")
        assert self.client.channels[1].audio_level_peak == -25  # 95 - 120
        assert self.client.channels[1].audio_level == -40  # 80 - 120
        assert self.client.channels[1].rf_level == -50  # 70 - 120

    def test_sample_channel_2(self):
        self.client._process_line("SAMPLE 2 ALL 000 100 090 060")
        assert self.client.channels[2].audio_level_peak == -20
        assert self.client.channels[2].audio_level == -30
        assert self.client.channels[2].rf_level == -60

    def test_sample_unknown_channel(self):
        """SAMPLE for non-existent channel should be ignored."""
        self.client._process_line("SAMPLE 9 ALL 100 090 060 000")
        self.callback.assert_not_called()

    def test_sample_too_short(self):
        self.client._process_line("SAMPLE 1 ALL 100")
        self.callback.assert_not_called()

    def test_sample_callback(self):
        self.client._process_line("SAMPLE 1 ALL 000 100 090 060")
        self.callback.assert_called_once()

    def test_sample_invalid_channel(self):
        self.client._process_line("SAMPLE XX ALL 100 090 060 000")
        self.callback.assert_not_called()


class TestBufferProcessing:
    """Test the TCP buffer processing."""

    def setup_method(self):
        self.client = ShureClient("192.168.1.1", num_channels=1)

    def test_single_complete_message(self):
        self.client._buffer = "< REP 1 CHAN_NAME {Test} >"
        self.client._process_buffer()
        assert self.client.channels[1].name == "Test"
        assert self.client._buffer == ""

    def test_multiple_messages(self):
        self.client._buffer = "< REP MODEL SLXD4 >< REP 1 CHAN_NAME {Mic} >"
        self.client._process_buffer()
        assert self.client.receiver.model == "SLXD4"
        assert self.client.channels[1].name == "Mic"

    def test_incomplete_message_preserved(self):
        self.client._buffer = "< REP MODEL SLXD4 >< REP 1 CHAN"
        self.client._process_buffer()
        assert self.client.receiver.model == "SLXD4"
        assert self.client._buffer == "< REP 1 CHAN"

    def test_empty_buffer(self):
        self.client._buffer = ""
        self.client._process_buffer()
        assert self.client._buffer == ""


class TestRegisterCallback:
    """Test callback registration."""

    def test_register_and_unregister(self):
        client = ShureClient("192.168.1.1")
        cb = MagicMock()
        unregister = client.register_callback(cb)

        client._notify_update()
        assert cb.call_count == 1

        unregister()
        client._notify_update()
        assert cb.call_count == 1  # Not called again


class TestSendCommand:
    """Test command sending."""

    @pytest.mark.asyncio
    async def test_send_command_not_connected(self):
        client = ShureClient("192.168.1.1")
        with pytest.raises(ConnectionError):
            await client.send_command("GET 0 ALL")

    @pytest.mark.asyncio
    async def test_send_command_formats_correctly(self):
        client = ShureClient("192.168.1.1")
        writer = MagicMock()
        writer.drain = AsyncMock()
        client._writer = writer

        await client.send_command("GET 0 ALL")
        writer.write.assert_called_once_with(b"< GET 0 ALL >")
        writer.drain.assert_awaited_once()


class TestConnect:
    """Test connect and disconnect."""

    @pytest.mark.asyncio
    async def test_connect(self):
        client = ShureClient("192.168.1.1")
        reader = AsyncMock()
        writer = MagicMock()
        writer.write = MagicMock()
        writer.drain = AsyncMock()
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()

        # Make reader.read return empty to end the listen loop quickly
        reader.read = AsyncMock(return_value=b"")

        with patch("asyncio.open_connection", return_value=(reader, writer)):
            await client.connect()
            assert client.connected is True
            assert client._listen_task is not None
            # Should have sent GET 0 ALL and SET 0 METER_RATE
            assert writer.write.call_count == 2

            await client.disconnect()
            assert client.connected is False
            assert client._writer is None

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self):
        client = ShureClient("192.168.1.1")
        # Should not raise
        await client.disconnect()
        assert client.connected is False


class TestCleanValue:
    """Test the _clean_value helper."""

    def test_removes_braces(self):
        client = ShureClient("192.168.1.1")
        assert client._clean_value("{hello}") == "hello"

    def test_trims_whitespace(self):
        client = ShureClient("192.168.1.1")
        assert client._clean_value("  hello  ") == "hello"

    def test_plain_value(self):
        client = ShureClient("192.168.1.1")
        assert client._clean_value("SLXD4") == "SLXD4"
