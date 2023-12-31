

from scapy.fields import FieldListField, PadField
from ptf.testutils import group

from base_test import *

from scapy.layers.inet6 import  _IPv6ExtHdr
from scapy.fields import *

_vla_routing_header_tlvs = {
    # RFC 8754 sect 8.2
    0: "Pad1 TLV",
    1: "Ingress Node TLV",  # draft 06
    2: "Egress Node TLV",  # draft 06
    4: "PadN TLV",
    5: "HMAC TLV",
}

class IPv6ExtHdrVlaRoutingTLV(Packet):
    name = "IPv6 Option Header Segment Routing - Generic TLV"
    # RFC 8754 sect 2.1
    fields_desc = [ByteEnumField("type", None, _vla_routing_header_tlvs),
                   ByteField("len", 0),
                   StrLenField("value", "", length_from=lambda pkt: pkt.len)]

    def extract_padding(self, p):
        return b"", p

    registered_sr_tlv = {}

    @classmethod
    def register_variant(cls):
        cls.registered_sr_tlv[cls.type.default] = cls

    @classmethod
    def dispatch_hook(cls, pkt=None, *args, **kargs):
        if pkt:
            tmp_type = ord(pkt[:1])
            return cls.registered_sr_tlv.get(tmp_type, cls)
        return cls


class IPv6ExtHdrVlaRoutingTLVIngressNode(IPv6ExtHdrVlaRoutingTLV):
    name = "IPv6 Option Header Segment Routing - Ingress Node TLV"
    # draft-ietf-6man-segment-routing-header-06 3.1.1
    fields_desc = [ByteEnumField("type", 1, _vla_routing_header_tlvs),
                   ByteField("len", 18),
                   ByteField("reserved", 0),
                   ByteField("flags", 0),
                   IP6Field("ingress_node", "::1")]


class IPv6ExtHdrVlaRoutingTLVEgressNode(IPv6ExtHdrVlaRoutingTLV):
    name = "IPv6 Option Header Segment Routing - Egress Node TLV"
    # draft-ietf-6man-segment-routing-header-06 3.1.2
    fields_desc = [ByteEnumField("type", 2, _vla_routing_header_tlvs),
                   ByteField("len", 18),
                   ByteField("reserved", 0),
                   ByteField("flags", 0),
                   IP6Field("egress_node", "::1")]


class IPv6ExtHdrVlaRoutingTLVPad1(IPv6ExtHdrVlaRoutingTLV):
    name = "IPv6 Option Header Segment Routing - Pad1 TLV"
    # RFC8754 sect 2.1.1.1
    fields_desc = [ByteEnumField("type", 0, _vla_routing_header_tlvs),
                   FieldLenField("len", None, length_of="padding", fmt="B"),
                   StrLenField("padding", b"\x00", length_from=lambda pkt: pkt.len)]  # noqa: E501


class IPv6ExtHdrVlaRoutingTLVPadN(IPv6ExtHdrVlaRoutingTLV):
    name = "IPv6 Option Header Segment Routing - PadN TLV"
    # RFC8754 sect 2.1.1.2
    fields_desc = [ByteEnumField("type", 4, _vla_routing_header_tlvs),
                   FieldLenField("len", None, length_of="padding", fmt="B"),
                   StrLenField("padding", b"\x00", length_from=lambda pkt: pkt.len)]  # noqa: E501


class IPv6ExtHdrVlaRoutingTLVHMAC(IPv6ExtHdrVlaRoutingTLV):
    name = "IPv6 Option Header Segment Routing - HMAC TLV"
    # RFC8754 sect 2.1.2
    fields_desc = [ByteEnumField("type", 5, _vla_routing_header_tlvs),
                   FieldLenField("len", None, length_of="hmac",
                                 adjust=lambda _, x: x + 48),
                   BitField("D", 0, 1),
                   BitField("reserved", 0, 15),
                   IntField("hmackeyid", 0),
                   StrLenField("hmac", "",
                               length_from=lambda pkt: pkt.len - 48)]

class IPv6ExtHdrVLA(_IPv6ExtHdr):

    name = "IPv6 Option Header VLA"
    # RFC8754 sect 2. + flag bits from draft 06
    fields_desc = [ByteEnumField("nh", 59, ipv6nh),
                   ByteField("len", None),
                BitField("address_type", 0, 2),
                   BitField("current_level", 0, 16),
                   BitField("number_of_levels", 0, 16),
                    BitField("number_of_source_levels", 0, 16),
                    BitField("pad", 0, 6),
                 FieldListField("addresses", [], ShortField("", 0), 
                                 count_from=lambda pkt: (pkt.number_of_levels), length_from = lambda pkt: pkt.number_of_levels * 2),
                FieldListField("source_addresses", [], ShortField("", 0), 
                                 count_from=lambda pkt: (pkt.number_of_source_levels), length_from=lambda pkt: pkt.number_of_source_levels * 2),
                PacketListField("tlv_objects", [],
                                   IPv6ExtHdrVlaRoutingTLV,
                                   length_from=lambda pkt: 8 * pkt.len - ((2 * (
                                       pkt.number_of_levels + pkt.number_of_source_levels)) + 1))
                            
    ]

    overload_fields = {IPv6: {"nh": 48}}
    def post_build(self, pkt, pay):
        if self.len is None:

            # The extension must be align on 8 bytes
            tmp_mod = (-len(pkt) + 8) % 8
            if tmp_mod == 1:
                tlv = IPv6ExtHdrVlaRoutingTLVPad1()
                pkt += raw(tlv)
            elif tmp_mod >= 2:
                # Add the padding extension
                tmp_pad = b"\x00" * (tmp_mod - 2)
                tlv = IPv6ExtHdrVlaRoutingTLVPadN(padding=tmp_pad)
                pkt += raw(tlv)

            tmp_len = (len(pkt) - 8) // 8
            pkt = pkt[:1] + struct.pack("B", tmp_len) + pkt[2:]

        if self.number_of_levels is None:
            tmp_len = len(self.addresses)
            if tmp_len:
                tmp_len -= 1
            pkt = pkt[:4] + struct.pack("B", tmp_len) + pkt[5:]

        if self.number_of_source_levels is None:
            tmp_len = len(self.source_addresses)
            if tmp_len:
                tmp_len -= 1
            pkt = pkt[:5] + struct.pack("B", tmp_len) + pkt[6:]

        if self.current_level is None:
            current_level = 0
            pkt = pkt[:3] + struct.pack("B", current_level) + pkt[4:]

        return _IPv6ExtHdr.post_build(self, pkt, pay)