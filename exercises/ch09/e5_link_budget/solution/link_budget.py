# SPDX-License-Identifier: MIT
"""Exercise 9.5: how many singles per second fit on an Ethernet link.

Each MDQ-R1 packet is one UDP datagram over IPv4 over Ethernet. On the wire a
datagram costs more than its payload: UDP and IPv4 headers, the Ethernet
header and frame check sequence, and the preamble and inter-frame gap that
every frame occupies on the wire. Numbers are bytes.
"""

UDP_HEADER = 8
IPV4_HEADER = 20           # without options
ETHERNET_HEADER = 14       # destination, source, EtherType (no VLAN tag)
ETHERNET_FCS = 4
PREAMBLE_SFD = 8
INTERFRAME_GAP = 12
MIN_FRAME = 64             # header + payload + FCS, padded up to this
MDQ_HEADER = 16
WORD = 8


# [snippet:wire]
def wire_bytes(udp_payload):
    """Bytes of link time that one datagram with `udp_payload` bytes occupies."""
    frame = ETHERNET_HEADER + IPV4_HEADER + UDP_HEADER + udp_payload + ETHERNET_FCS
    return max(frame, MIN_FRAME) + PREAMBLE_SFD + INTERFRAME_GAP


def packet_payload(words_per_packet):
    return MDQ_HEADER + WORD * words_per_packet


def wire_bytes_per_single(words_per_packet):
    return wire_bytes(packet_payload(words_per_packet)) / words_per_packet


def max_singles_per_s(link_bits_per_s, words_per_packet):
    """The singles rate that fills the link completely."""
    return link_bits_per_s / 8.0 / wire_bytes_per_single(words_per_packet)
# [/snippet:wire]


def utilization(singles_per_s, words_per_packet, link_bits_per_s):
    return singles_per_s / max_singles_per_s(link_bits_per_s, words_per_packet)


def packets_per_s(singles_per_s, words_per_packet):
    return singles_per_s / words_per_packet
