import { db } from '$lib/server/db';
import type { PageServerLoad, Actions } from './$types';
import { env } from '$env/dynamic/private';

export const load: PageServerLoad = async ({ cookies }) => {
    const authed = cookies.get('pin_auth') === 'true';
    if (!authed) return { leads: { main: [], call: [] }, revenueRecords: [], authed: false };

    try {
        const rs = await db.execute("SELECT * FROM leads ORDER BY id DESC");
        const leads = rs.rows;
        
        let revenueRecords: any[] = [];
        try {
            const revRs = await db.execute("SELECT * FROM revenue_records ORDER BY period DESC, id DESC");
            revenueRecords = revRs.rows as any[];
        } catch (revErr) {
            console.error("Failed to load revenue records", revErr);
        }

        // Group leads by stage
        const main = leads.filter(l => l.stage === 'main');
        const call = leads.filter(l => l.stage === 'call');

        const sortLeads = (a: any, b: any) => {
            const dateA = String(a.date || "");
            const dateB = String(b.date || "");
            if (dateA !== dateB) {
                return dateB.localeCompare(dateA); // New to old
            }
            return (Number(b.id) || 0) - (Number(a.id) || 0);
        };
        
        return {
            leads: {
                main: main.sort(sortLeads) as any[],
                call: call.sort(sortLeads) as any[]
            },
            revenueRecords,
            authed: true
        };
    } catch (e) {
        console.error("Failed to load leads", e);
        return { leads: { main: [], call: [] }, revenueRecords: [], authed: true };
    }
};

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
        const revenue = data.get('revenue');

        if (id && status) {
            if (revenue) {
                await db.execute({
                    sql: 'UPDATE leads SET status = ?, revenue = ? WHERE id = ?',
                    args: [status, revenue, id]
                });

                // Also log to revenue_records if amount > 0
                const numRev = Number(revenue);
                if (numRev > 0) {
                    try {
                        const leadRes = await db.execute({ sql: 'SELECT business FROM leads WHERE id = ?', args: [id] });
                        const bName = leadRes.rows[0]?.business?.toString() || 'Converted Lead';
                        const period = new Date().toISOString().slice(0, 7);
                        const date = new Date().toISOString().split('T')[0];
                        await db.execute({
                            sql: 'INSERT INTO revenue_records (lead_id, business, type, amount, period, notes, date) VALUES (?, ?, ?, ?, ?, ?, ?)',
                            args: [id, bName, 'one_time', numRev, period, 'Conversion payment', date]
                        });
                    } catch (err) {
                        console.error("Failed to insert revenue record on conversion", err);
                    }
                }
            } else {
                await db.execute({
                    sql: 'UPDATE leads SET status = ? WHERE id = ?',
                    args: [status, id]
                });
            }
        }
        return { success: true };
    },
    addRevenueRecord: async ({ request, cookies }) => {
        if (cookies.get('pin_auth') !== 'true') return { success: false };
        const data = await request.formData();
        const lead_id = data.get('lead_id') ? Number(data.get('lead_id')) : null;
        const business = data.get('business')?.toString().trim();
        const type = data.get('type')?.toString().trim() || 'one_time';
        const amount = Number(data.get('amount')) || 0;
        const period = data.get('period')?.toString().trim() || new Date().toISOString().slice(0, 7);
        const notes = data.get('notes')?.toString().trim() || '';
        const date = new Date().toISOString().split('T')[0];

        if (business && amount > 0) {
            await db.execute({
                sql: 'INSERT INTO revenue_records (lead_id, business, type, amount, period, notes, date) VALUES (?, ?, ?, ?, ?, ?, ?)',
                args: [lead_id, business, type, amount, period, notes, date]
            });
        }
        return { success: true };
    },
    deleteRevenueRecord: async ({ request, cookies }) => {
        if (cookies.get('pin_auth') !== 'true') return { success: false };
        const data = await request.formData();
        const id = data.get('id');
        if (id) {
            await db.execute({
                sql: 'DELETE FROM revenue_records WHERE id = ?',
                args: [id]
            });
        }
        return { success: true };
    },
    addLead: async ({ request, cookies }) => {
        if (cookies.get('pin_auth') !== 'true') return { success: false };
        const data = await request.formData();
        const business = data.get('business');
        const remarks = data.get('remarks');
        const segment = data.get('segment')?.toString().trim() || 'regular';
        const status = data.get('status') || 'Pending';
        const date = new Date().toISOString().split('T')[0];

        if (business) {
            await db.execute({
                sql: 'INSERT INTO leads (stage, business, remarks, status, date, segment) VALUES (?, ?, ?, ?, ?, ?)',
                args: ['main', business, remarks, status, date, segment]
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
    moveToFollowUp: async ({ request, cookies }) => {
        if (cookies.get('pin_auth') !== 'true') return { success: false };
        const data = await request.formData();
        const id = data.get('id');
        if (id) {
            await db.execute({
                sql: 'UPDATE leads SET stage = ? WHERE id = ?',
                args: ['call', id]
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
