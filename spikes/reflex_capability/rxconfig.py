import reflex as rx

# Throwaway pilot config (issue #108). Not wired into main; lives only in spikes/.
config = rx.Config(
    app_name="reflex_capability",
    # keep the spike self-contained; no telemetry, no db
    telemetry_enabled=False,
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
)
