# clients/__init__.py
from .qbittorrent import QBittorrentClient

def get_torrent_client(config):
    """
    Factory function to create the appropriate torrent client instance.
    
    Args:
        config: Application configuration dict containing TORRENT_CLIENT_TYPE
        
    Returns:
        TorrentClient instance (QBittorrentClient, etc.)
        
    Raises:
        ValueError: If unsupported client type is specified
    """
    client_type = config.get("TORRENT_CLIENT_TYPE", "qbittorrent").lower()
    
    if client_type == "qbittorrent":
        return QBittorrentClient(config)
    
    # Future expansion:
    # elif client_type == "transmission":
    #     return TransmissionClient(config)
    # elif client_type == "deluge":
    #     return DelugeClient(config)
        
    raise ValueError(f"Unsupported torrent client type: {client_type}")
