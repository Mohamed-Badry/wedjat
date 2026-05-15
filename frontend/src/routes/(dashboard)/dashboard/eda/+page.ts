import type { PageLoad } from './$types';
import { env } from '$env/dynamic/public';

export const load: PageLoad = async ({ fetch }) => {
    const apiUrl = typeof window !== "undefined" ? (env.PUBLIC_API_URL || "http://127.0.0.1:8000") : "http://backend:8000"; console.log("SSR URL EVAL:", apiUrl, "window is:", typeof window);
    
    try {
        const satsRes = await fetch(`${apiUrl}/api/satellites`);
        let satellites = [];
        if (satsRes.ok) {
            const data = await satsRes.json();
            satellites = data.satellites;
        }

        return {
            satellites
        };
    } catch (e) {
        console.error("Error fetching insights data:", e);
        return {
            satellites: [],
            error: "Could not connect to the backend API."
        };
    }
};
