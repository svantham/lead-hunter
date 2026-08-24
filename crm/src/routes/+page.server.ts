import { db } from '$lib/server/db';
import type { PageServerLoad, Actions } from './$types';

export const load: PageServerLoad = async () => {
    try {
        const rs = await db.execute("SELECT * FROM leads ORDER BY id DESC");
        const leads = rs.rows;
        
        // Group leads by stage
        const main = leads.filter(l => l.stage === 'main');
        const call = leads.filter(l => l.stage === 'call');

        const statusOrder: Record<string, number> = {
            'Pending': 1,
            'Contacted': 2,
            'Interested': 3,
            'Converted': 4,
            'Rejected': 5
        };

        const sortLeads = (a: any, b: any) => {
            const orderA = statusOrder[a.status] || 6;
            const orderB = statusOrder[b.status] || 6;
            return orderA - orderB;
        };
        
        return {
            leads: {
                main: main.sort(sortLeads) as any[],
                call: call.sort(sortLeads) as any[]
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
    },
    moveLead: async ({ request }) => {
        const data = await request.formData();
        const id = data.get('id');
        const status = data.get('status');

        if (id && status) {
            await db.execute({
                sql: 'UPDATE leads SET stage = ?, status = ? WHERE id = ?',
                args: ['main', status, id]
            });
        }
        return { success: true };
    }
};
