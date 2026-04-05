"""Tests for Shure Wireless sensor entities."""

from __future__ import annotations

from custom_components.shure_wireless.shure_client import ChannelState


class TestBatteryLevelValues:
    """Test battery level sensor value logic."""

    def test_battery_charge_reported(self):
        channel = ChannelState(battery_charge=75)
        assert channel.battery_charge == 75

    def test_battery_charge_none(self):
        channel = ChannelState()
        assert channel.battery_charge is None

    def test_battery_bars_attribute(self):
        channel = ChannelState(battery_bars=4, battery_type="LITHIUM_ION")
        assert channel.battery_bars == 4
        assert channel.battery_type == "LITHIUM_ION"

    def test_battery_health_attribute(self):
        channel = ChannelState(battery_health=95, battery_cycle=50, battery_temp_c=25)
        assert channel.battery_health == 95
        assert channel.battery_cycle == 50
        assert channel.battery_temp_c == 25


class TestRFLevelValues:
    """Test RF level sensor value logic."""

    def test_rf_level_normal(self):
        channel = ChannelState(rf_level=-50)
        assert channel.rf_level == -50

    def test_rf_level_default_no_signal(self):
        channel = ChannelState()
        assert channel.rf_level == -120

    def test_rf_attributes(self):
        channel = ChannelState(
            frequency="470.125",
            interference_status="NONE",
            encryption_status="OK",
        )
        assert channel.frequency == "470.125"
        assert channel.interference_status == "NONE"
        assert channel.encryption_status == "OK"


class TestAudioLevelValues:
    """Test audio level sensor value logic."""

    def test_audio_level_normal(self):
        channel = ChannelState(audio_level=-30)
        assert channel.audio_level == -30

    def test_audio_level_default(self):
        channel = ChannelState()
        assert channel.audio_level == -120

    def test_audio_attributes(self):
        channel = ChannelState(
            audio_level_peak=-25,
            audio_gain=12,
            audio_mute="OFF",
            tx_mute_status="OFF",
        )
        assert channel.audio_level_peak == -25
        assert channel.audio_gain == 12
        assert channel.audio_mute == "OFF"
        assert channel.tx_mute_status == "OFF"


class TestChannelNameValues:
    """Test channel name sensor value logic."""

    def test_channel_name(self):
        channel = ChannelState(name="Mic 1")
        assert channel.name == "Mic 1"

    def test_channel_name_empty(self):
        channel = ChannelState()
        assert channel.name == ""

    def test_tx_attributes(self):
        channel = ChannelState(tx_model="SLXD1", tx_device_id="TX-001")
        assert channel.tx_model == "SLXD1"
        assert channel.tx_device_id == "TX-001"


class TestBatteryRuntimeValues:
    """Test battery runtime sensor value logic."""

    def test_runtime_normal(self):
        channel = ChannelState(battery_runtime=120)
        assert channel.battery_runtime == 120

    def test_runtime_none(self):
        channel = ChannelState()
        assert channel.battery_runtime is None


class TestGainValues:
    """Test gain sensor value logic."""

    def test_gain_normal(self):
        channel = ChannelState(audio_gain=12)
        assert channel.audio_gain == 12

    def test_gain_none(self):
        channel = ChannelState()
        assert channel.audio_gain is None


class TestFeedbackReductionValues:
    """Test feedback reduction sensor value logic."""

    def test_fd_mode_on(self):
        channel = ChannelState(fd_mode="ON")
        assert channel.fd_mode == "ON"

    def test_fd_mode_off(self):
        channel = ChannelState(fd_mode="OFF")
        assert channel.fd_mode == "OFF"

    def test_fd_mode_default(self):
        channel = ChannelState()
        assert channel.fd_mode == ""


class TestAntennaValues:
    """Test antenna sensor value logic."""

    def test_antenna_ab(self):
        channel = ChannelState(antenna="AB")
        assert channel.antenna == "AB"

    def test_antenna_default(self):
        channel = ChannelState()
        assert channel.antenna == "XX"


class TestTxPowerValues:
    """Test TX power sensor value logic."""

    def test_tx_power_normal(self):
        channel = ChannelState(tx_rf_power="NORMAL")
        assert channel.tx_rf_power == "NORMAL"

    def test_tx_power_default(self):
        channel = ChannelState()
        assert channel.tx_rf_power == ""


class TestTxOffsetValues:
    """Test TX offset sensor value logic."""

    def test_tx_offset_value(self):
        channel = ChannelState(tx_offset=10)
        assert channel.tx_offset == 10

    def test_tx_offset_none(self):
        channel = ChannelState()
        assert channel.tx_offset is None


class TestSquelchValues:
    """Test squelch sensor value logic."""

    def test_squelch_value(self):
        channel = ChannelState(squelch=5)
        assert channel.squelch == 5

    def test_squelch_none(self):
        channel = ChannelState()
        assert channel.squelch is None
