/**
 * Sky-Trace FR24 Reverse Proxy Worker
 *
 * Proxies requests to FlightRadar24 API to bypass Cloudflare bot protection.
 * Usage: https://<worker-domain>/?url=<encoded-fr24-url>
 *
 * Based on: https://github.com/DimaD16/cloudflare-workers-fr24-proxy
 * Free tier: 100,000 requests/day
 */

export default {
	async fetch(request) {
		const url = new URL(request.url);
		const targetUrl = url.searchParams.get("url");

		if (!targetUrl) {
			return new Response(JSON.stringify({ error: "Missing url parameter" }), {
				status: 400,
				headers: { "Content-Type": "application/json" },
			});
		}

		// Only allow proxying to FlightRadar24 domains
		let parsedTarget;
		try {
			parsedTarget = new URL(targetUrl);
		} catch {
			return new Response(JSON.stringify({ error: "Invalid url parameter" }), {
				status: 400,
				headers: { "Content-Type": "application/json" },
			});
		}

		const allowedHosts = [
			"data-cloud.flightradar24.com",
			"data-live.flightradar24.com",
			"api.flightradar24.com",
			"www.flightradar24.com",
			"cdn.flightradar24.com",
		];
		if (!allowedHosts.includes(parsedTarget.hostname)) {
			return new Response(
				JSON.stringify({ error: "Target host not allowed" }),
				{
					status: 403,
					headers: { "Content-Type": "application/json" },
				},
			);
		}

		const acceptHeader = request.headers.get("Accept") || "*/*";

		const headers = {
			"User-Agent":
				"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
			Accept: acceptHeader,
			"X-Requested-With": "com.flightradar24.iphone",
		};

		try {
			const response = await fetch(targetUrl, { headers });

			return new Response(response.body, {
				status: response.status,
				headers: {
					"Content-Type":
						response.headers.get("Content-Type") || "application/json",
					"Access-Control-Allow-Origin": "*",
				},
			});
		} catch (e) {
			return new Response(JSON.stringify({ error: e.message }), {
				status: 500,
				headers: { "Content-Type": "application/json" },
			});
		}
	},
};
