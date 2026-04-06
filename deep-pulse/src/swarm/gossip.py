#!/usr/bin/env python3
"""
Deep Pulse — Pulse Socket / Tor-Aware Gossip Protocol
"""

import asyncio
import logging
import json
import struct

logger = logging.getLogger(__name__)

class PulseGossip:
    """
    Lightweight Asyncio Tor-Aware SOCKS5 socket wrapper.
    Replaces heavy library dependencies with native TCP pipes.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 4110, tor_proxy: tuple = ("127.0.0.1", 9050)):
        self.host = host
        self.port = port
        self.tor_proxy_host = tor_proxy[0]
        self.tor_proxy_port = tor_proxy[1]
        self.server = None

    async def _socks5_connect(self, target_host: str, target_port: int):
        """
        Manually negotiates the SOCKS5 byte authentication to route TCP through Tor.
        Allows native .onion resolution without PySocks/AioSocks.
        """
        try:
            reader, writer = await asyncio.open_connection(self.tor_proxy_host, self.tor_proxy_port)
            
            # 1. Hello (No Auth)
            writer.write(b"\x05\x01\x00")
            await writer.drain()
            response = await reader.read(2)
            if response != b"\x05\x00":
                raise ConnectionError("SOCKS5 Proxy rejected NO-AUTH hello.")

            # 2. Connect
            host_bytes = target_host.encode("utf-8")
            packet = struct.pack(
                "!BBBB", 
                0x05,  # SOCKS5
                0x01,  # CONNECT
                0x00,  # RSV
                0x03   # DOMAINNAME
            ) + struct.pack("!B", len(host_bytes)) + host_bytes + struct.pack("!H", target_port)
            
            writer.write(packet)
            await writer.drain()
            
            resp = await reader.read(10)
            if len(resp) < 2 or resp[1] != 0x00:
                raise ConnectionError("SOCKS5 Proxy rejected Target connection.")

            logger.info(f"Tor Route Established to {target_host}:{target_port}")
            return reader, writer
        except Exception as e:
            logger.error(f"SOCKS5 Proxy Negotiation failed: {e}")
            return None, None

    async def broadcast_cid(self, target_node: str, envelope: dict):
        """Broadcasts a Deep Ledger standard entry to a specific node."""
        logger.info(f"Broadcasting CID {envelope.get('id')} to {target_node}")
        
        # Determine if onions are routed via Tor, local nodes over direct TCP
        reader = writer = None
        if target_node.endswith(".onion"):
            reader, writer = await self._socks5_connect(target_node, 4110)
        else:
            try:
                reader, writer = await asyncio.open_connection(target_node, 4110)
            except Exception as e:
                # logger.error(f"Direct connection to {target_node} failed: {e}")
                pass

        if writer:
            try:
                payload = json.dumps(envelope).encode("utf-8")
                writer.write(payload + b"\n")
                await writer.drain()
                writer.close()
                await writer.wait_closed()
                logger.debug(f"Broadcast successful to {target_node}.")
            except Exception as e:
                logger.error(f"Failed to transmit pipeline payload: {e}")

    async def broadcast_interests(self, target_nodes: list, interest_cid: str, sectors: list):
        """
        Broadcasts an 'Interest CID' (Subscription Manifest) to the swarm.
        This signals that this node is a 'known interested party' for specific sectors.
        """
        envelope = {
            "@context": "Deep Pulse Subscription Manifest v1.0",
            "id": interest_cid,
            "type": "interest_broadcast",
            "sectors": sectors
        }
        for node in target_nodes:
            await self.broadcast_cid(node, envelope)

    async def _handle_incoming(self, reader, writer):
        """Handles incoming P2P Gossip blocks."""
        addr = writer.get_extra_info('peername')
        # logger.info(f"Incoming connection from {addr}")
        
        data = await reader.readline()
        if data:
            try:
                message = json.loads(data.decode("utf-8").strip())
                context = message.get("@context")
                
                if context == "Deep Ledger Intelligence Standard v1.0":
                    logger.info(f"Received valid Protocol block: CID {message.get('id')}")
                    # TODO: Pass to Consensus engine
                elif context == "Deep Pulse Subscription Manifest v1.0":
                    sectors = message.get("sectors", [])
                    logger.info(f"Node {addr} broadcasted interest in sectors: {sectors}")
                    # TODO: Prioritize pushing relevant pulses to this address
                else:
                    logger.warning(f"Rejected non-standard payload from {addr}")
            except json.JSONDecodeError:
                logger.warning(f"Rejected invalid JSON payload from {addr}")

        writer.close()
        try:
            await writer.wait_closed()
        except:
            pass

    async def start_server(self):
        """Spins up the native listening socket."""
        self.server = await asyncio.start_server(self._handle_incoming, self.host, self.port)
        addr = self.server.sockets[0].getsockname()
        logger.info(f"PulseGossip Server listening on {addr}")

    async def stop_server(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("PulseGossip Server fully shutdown.")
