import type { PageLoad } from './$types';
import { env } from '$env/dynamic/public';

export const load: PageLoad = async ({ fetch }) => {
    const apiUrl = env.PUBLIC_API_URL || 'http://127.0.0.1:8000';
    
    try {
        const [summaryRes, statusRes] = await Promise.all([
            fetch(`${apiUrl}/api/dashboard/summary`),
            fetch(`${apiUrl}/api/status`)
        ]);

        return {
            summary: summaryRes.ok ? await summaryRes.json() : null,
            systemStatus: statusRes.ok ? await statusRes.json() : null
        };
    } catch (e) {
        console.error("Error fetching dashboard data:", e);
        return {
            summary: null,
            systemStatus: null,
            error: "Could not connect to the backend API."
        };
    }
};
