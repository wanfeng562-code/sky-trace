import { createRouter, createWebHistory } from "vue-router";

import MapView from "../views/MapView.vue";
import StatsView from "../views/StatsView.vue";
import PlaybackView from "../views/PlaybackView.vue";

const router = createRouter({
	history: createWebHistory(),
	routes: [
		{
			path: "/",
			name: "map",
			component: MapView,
		},
		{
			path: "/stats",
			name: "stats",
			component: StatsView,
		},
		{
			path: "/playback",
			name: "playback",
			component: PlaybackView,
		},
	],
});

export default router;
