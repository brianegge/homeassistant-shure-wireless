"""Tests for Shure ACN multicast discovery."""

from custom_components.shure_wireless.discovery import (
    ShureDiscoveryProtocol,
    _parse_acn_announcement,
)


class TestParseAcnAnnouncement:
    """Test parsing of ACN SLP multicast announcements."""

    SAMPLE_PAYLOAD = (
        b'\x02\x07\x00\x01P\x00\x00\x00\x00\x00"=\x00\x02en\x00\x00\x01;'
        b"(cid=DDB0C8C5-0000-11DD-A000-000EDDCCCCCC),"
        b"(acn-fctn=SLXD4DE_RX),"
        b"(acn-uacn=SLXD4DE G57),"
        b"(acn-services=esta.dmp),"
        b"(csl-esta.dmp=esta.sdt/192.168.3.21:57383;esta.dmp/cd:320CA2FC-2932-11ED-8BBF-0015C5F3F612),"
        b"(device-description=$:tftp://192.168.3.21/$.ddl),"
        b"(csl-esta.dmp.values=version:1_interfaceId:65552_extVersion:1)."
    )

    def test_parse_slxd4de(self):
        """Test parsing a SLXD4DE announcement."""
        result = _parse_acn_announcement(self.SAMPLE_PAYLOAD, "192.168.3.21")
        assert result is not None
        assert result.host == "192.168.3.21"
        assert result.model == "SLXD4DE"
        assert result.name == "SLXD4DE G57"
        assert result.cid == "DDB0C8C5-0000-11DD-A000-000EDDCCCCCC"
        assert result.num_channels == 2

    def test_parse_slxd4_single(self):
        """Test parsing a single-channel SLXD4."""
        payload = b"(cid=AABB1122-0000-11DD-A000-000000000000),(acn-fctn=SLXD4_RX),(acn-uacn=My Receiver)"
        result = _parse_acn_announcement(payload, "10.0.0.5")
        assert result is not None
        assert result.model == "SLXD4"
        assert result.num_channels == 1
        assert result.name == "My Receiver"

    def test_parse_slxd4d_dual(self):
        """Test parsing a dual-channel SLXD4D."""
        payload = b"(cid=CCDD3344-0000-11DD-A000-000000000000),(acn-fctn=SLXD4D_RX),(acn-uacn=Dual RX)"
        result = _parse_acn_announcement(payload, "10.0.0.6")
        assert result is not None
        assert result.model == "SLXD4D"
        assert result.num_channels == 2

    def test_parse_no_function(self):
        """Test that announcements without acn-fctn are ignored."""
        payload = b"(cid=AABB1122-0000-11DD-A000-000000000000),(acn-services=foo)"
        result = _parse_acn_announcement(payload, "10.0.0.1")
        assert result is None

    def test_parse_non_receiver_ignored(self):
        """Test that non-receiver devices like the Shure Updater are ignored."""
        payload = b"(cid=AABB-0000),(acn-fctn=SOFTWARE_UPDATE_UTILITY),(acn-uacn=SHURE SOFTWARE UPDATE UTILITY)"
        result = _parse_acn_announcement(payload, "10.0.0.1")
        assert result is None

    def test_parse_empty_data(self):
        """Test that empty data returns None."""
        result = _parse_acn_announcement(b"", "10.0.0.1")
        assert result is None

    def test_parse_garbage_data(self):
        """Test that garbage data returns None."""
        result = _parse_acn_announcement(b"\xff\xfe\x00\x01", "10.0.0.1")
        assert result is None


class TestDiscoveryProtocol:
    """Test the ShureDiscoveryProtocol."""

    SAMPLE_PAYLOAD = b"(cid=DDB0C8C5-0000-11DD-A000-000EDDCCCCCC),(acn-fctn=SLXD4DE_RX),(acn-uacn=SLXD4DE G57)"

    def test_first_discovery_is_new(self):
        """Test that first discovery of a device is flagged as new."""
        protocol = ShureDiscoveryProtocol()
        results = []
        protocol.register_callback(lambda device, is_new: results.append((device, is_new)))

        protocol.datagram_received(self.SAMPLE_PAYLOAD, ("192.168.3.21", 8427))

        assert len(results) == 1
        assert results[0][1] is True  # is_new
        assert results[0][0].host == "192.168.3.21"

    def test_second_discovery_not_new(self):
        """Test that repeated discovery is not flagged as new."""
        protocol = ShureDiscoveryProtocol()
        results = []
        protocol.register_callback(lambda device, is_new: results.append((device, is_new)))

        protocol.datagram_received(self.SAMPLE_PAYLOAD, ("192.168.3.21", 8427))
        protocol.datagram_received(self.SAMPLE_PAYLOAD, ("192.168.3.21", 8427))

        assert len(results) == 2
        assert results[0][1] is True
        assert results[1][1] is False

    def test_devices_property(self):
        """Test the devices property returns discovered devices."""
        protocol = ShureDiscoveryProtocol()
        assert protocol.devices == {}

        protocol.datagram_received(self.SAMPLE_PAYLOAD, ("192.168.3.21", 8427))
        devices = protocol.devices
        assert len(devices) == 1
        assert "DDB0C8C5-0000-11DD-A000-000EDDCCCCCC" in devices

    def test_non_shure_packet_ignored(self):
        """Test that non-Shure packets are silently ignored."""
        protocol = ShureDiscoveryProtocol()
        results = []
        protocol.register_callback(lambda device, is_new: results.append(device))

        protocol.datagram_received(b"random data with no acn fields", ("10.0.0.1", 8427))

        assert len(results) == 0

    def test_callback_error_does_not_propagate(self):
        """Test that callback errors don't crash the protocol."""
        protocol = ShureDiscoveryProtocol()

        def bad_callback(device, is_new):
            raise RuntimeError("oops")

        protocol.register_callback(bad_callback)
        # Should not raise
        protocol.datagram_received(self.SAMPLE_PAYLOAD, ("192.168.3.21", 8427))
