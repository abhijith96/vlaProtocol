
from scapy.layers.inet6 import  _IPv6ExtHdr;
from scapy.fields import FieldListField, PadField
from ptf.testutils import group

from base_test import *

class IPv6ExtHdrVLA(_IPv6ExtHdr):

    name = "IPv6 Option Header Segment Routing"
    # RFC8754 sect 2. + flag bits from draft 06
    fields_desc = [ByteEnumField("nh", 59, ipv6nh),
                   ByteField("len", None),
                BitField("address_type", 0, 2),
                   BitField("current_level", 0, 16),
                   BitField("number_of_levels", 0, 16),
                    PadField(BitField("pad", 0, 4), 8),
                 FieldListField("addresses", [], BitField("number_of_levels_2", 0, 16), 
                                 count_from=lambda pkt: (pkt.num_levels))
    ]

    overload_fields = {IPv6: {"nh": 48}}

    def post_build(self, pkt, pay):

        if self.len is None:

            # The extension must be align on 8 bytes
            tmp_mod = (-len(pkt) + 8) % 8
            if tmp_mod == 1:
                tlv = IPv6ExtHdrSegmentRoutingTLVPad1()
                pkt += raw(tlv)
            elif tmp_mod >= 2:
                # Add the padding extension
                tmp_pad = b"\x00" * (tmp_mod - 2)
                tlv = IPv6ExtHdrSegmentRoutingTLVPadN(padding=tmp_pad)
                pkt += raw(tlv)

            tmp_len = (len(pkt) - 8) // 8
            pkt = pkt[:1] + struct.pack("B", tmp_len) + pkt[2:]

        if self.num_levels is None:
            tmp_len = len(self.addresses)
            if tmp_len:
                tmp_len -= 1
            pkt = pkt[:3] + struct.pack("B", tmp_len) + pkt[4:]

        if self.current_level is None:
            self.current_level = 0
            pkt = pkt[:4] + struct.pack("B", self.current_level) + pkt[5:]

        return _IPv6ExtHdr.post_build(self, pkt, pay)