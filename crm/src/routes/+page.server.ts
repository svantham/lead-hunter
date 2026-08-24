import { db } from '$lib/server/db';
import type { PageServerLoad, Actions } from './$types';

export const load: PageServerLoad = async () => {
    try {
        const rs = await db.execute("SELECT * FROM leads ORDER BY id DESC");
        
        // Group leads by stage
        const main = rs.rows.filter(r => r.stage === 'main');
        const call = rs.rows.filter(r => r.stage === 'call');
        
        return {
            leads: {
                main: main as any[],
                call: call as any[]
            }
        };
    } catch (e) {
        console.error("Failed to fetch leads:", e);
        return {
            leads: { main: [], call: [] }
        };
    }
};

export const actions: Actions = {
    updateStatus: async ({ request }) => {
        const data = await request.formData();
        const id = data.get('id');
        const status = data.get('status');

        if (id && status) {
            await db.execute({
                sql: 'UPDATE leads SET status = ? WHERE id = ?',
                args: [status, id]
            });
        }
        return { success: true };
    }
};
