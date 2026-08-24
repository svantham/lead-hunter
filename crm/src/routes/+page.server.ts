import { db } from '$lib/server/db';
import type { PageServerLoad, Actions } from './$types';

export const load: PageServerLoad = async ({ cookies }) => {
    const authed = cookies.get('pin_auth') === 'true';
    if (!authed) return { leads: { main: [], call: [] }, authed: false };

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
            },
            authed: true
        };
    } catch (e) {
        console.error("Failed to load leads", e);
        return { leads: { main: [], call: [] }, authed: true };
    }
};

import { env } from '$env/dynamic/private';

export const actions: Actions = {
    login: async ({ request, cookies }) => {
        const data = await request.formData();
        const pin = data.get('pin');
        if (pin === (env.CRM_PIN || '0000')) {
            cookies.set('pin_auth', 'true', { path: '/', maxAge: 60 * 60 * 24 * 30 }); // 30 days
            return { success: true };
        }
        return { success: false, error: 'Invalid PIN' };
    },
    updateStatus: async ({ request, cookies }) => {
        if (cookies.get('pin_auth') !== 'true') return { success: false };
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
    moveLead: async ({ request, cookies }) => {
        if (cookies.get('pin_auth') !== 'true') return { success: false };
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
    },
    deleteLead: async ({ request, cookies }) => {
        if (cookies.get('pin_auth') !== 'true') return { success: false };
        const data = await request.formData();
        const id = data.get('id');

        if (id) {
            await db.execute({
                sql: 'DELETE FROM leads WHERE id = ?',
                args: [id]
            });
        }
        return { success: true };
    }
};
