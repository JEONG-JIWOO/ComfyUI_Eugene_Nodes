"""
Web service handlers for LoRA preset management
"""

from aiohttp import web
from .preset_nodes import PresetSelector


async def get_presets(request):
    """API endpoint to get all presets data"""
    try:
        selector = PresetSelector()
        return web.json_response({
            "subfolders": selector.all_subfolders,
            "presets": [
                {"path": path, "display_name": display_name}
                for path, display_name in selector.all_presets
            ]
        })
    except Exception as e:
        print(f"Error in get_presets API: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def refresh_presets(request):
    """API endpoint to refresh preset data"""
    try:
        updated_data = PresetSelector.update_data()
        return web.json_response({
            "status": "success",
            "presets": [
                {"path": path, "display_name": display_name}
                for path, display_name in updated_data["presets"]
            ]
        })
    except Exception as e:
        print(f"Error in refresh_presets API: {e}")
        return web.json_response({"error": str(e)}, status=500)


def setup_routes(server):
    """Setup web routes for LoRA preset management"""
    # Add routes with correct API paths
    for route in ["/lora_presets", "/api/lora_presets"]:  # Support both paths for compatibility
        server.app.router.add_route("GET", route, get_presets)
        server.app.router.add_route("POST", route, get_presets)

    for route in ["/lora_presets/refresh", "/api/lora_presets/refresh"]:
        server.app.router.add_route("GET", route, refresh_presets)
        server.app.router.add_route("POST", route, refresh_presets)