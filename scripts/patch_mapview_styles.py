from pathlib import Path

p = Path(__file__).resolve().parents[1] / "client" / "src" / "views" / "MapView.vue"
text = p.read_text(encoding="utf-8")
marker = "\t/* REMOVED_OLD_STYLES */"
end_marker = "</style>"
idx = text.index(marker)
end = text.rindex(end_marker)

new_tail = """
	:global(.maplibregl-ctrl-bottom-right) {
		right: 12px;
		bottom: 12px;
	}

	:global(.maplibregl-ctrl-bottom-right .maplibregl-ctrl-group) {
		border-radius: var(--radius-md);
		box-shadow: var(--shadow-sm);
		border: 1px solid var(--border);
		overflow: hidden;
	}

	:global(.maplibregl-ctrl-bottom-right .sky-geolocate-control) {
		margin-bottom: 8px;
	}

	:global(.maplibregl-ctrl-bottom-right .maplibregl-ctrl-group + .sky-geolocate-control) {
		margin-bottom: 0;
	}

	:global(.sky-geolocate-btn) {
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--text-secondary);
	}

	:global(.sky-geolocate-btn:hover) {
		background-color: var(--bg-elevated);
	}

	:global(.maplibregl-ctrl-bottom-left) {
		left: 12px;
		bottom: 12px;
	}

	:global(.maplibregl-ctrl-bottom-left .maplibregl-ctrl-scale) {
		border: 1px solid var(--border);
		border-top: 2px solid var(--text-muted);
		background: var(--bg-surface);
		color: var(--text-secondary);
		font-size: 11px;
		padding: 2px 6px;
		border-radius: var(--radius-sm);
	}
</style>"""

text = text[:idx] + new_tail
p.write_text(text, encoding="utf-8")
print("styles patched")
