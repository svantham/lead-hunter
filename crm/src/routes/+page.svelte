<script lang="ts">
    import { enhance } from '$app/forms';
    import MessageCircle from 'lucide-svelte/icons/message-circle';
    import Phone from 'lucide-svelte/icons/phone';
    import Globe from 'lucide-svelte/icons/globe';
    import ChevronDown from 'lucide-svelte/icons/chevron-down';
    import Trash2 from 'lucide-svelte/icons/trash-2';
    let { data } = $props();
    
    let activeTab = $state<'main' | 'call'>('main');
    let openDropdown = $state<number | null>(null);
    let scriptModalLead = $state<any>(null);
    let submittingId = $state<number | null>(null);
    
    // Funky colors for status badges
    const statusColors: Record<string, string> = {
        'Pending': 'bg-yellow-200 text-yellow-900 border-yellow-900',
        'Contacted': 'bg-blue-200 text-blue-900 border-blue-900',
        'Interested': 'bg-green-200 text-green-900 border-green-900',
        'Converted': 'bg-fuchsia-200 text-fuchsia-900 border-fuchsia-900',
        'Rejected': 'bg-red-200 text-red-900 border-red-900',
    };
    
    function getStatusColor(status: string) {
        return statusColors[status] || 'bg-gray-200 text-gray-900 border-gray-900';
    }

    function getPitchUrl(phone: string, business: string) {
        if (!phone) return '';
        const text = `*${business}*,

_Innum Excel use panitu irukingala?  Unga business work ah automate pananuma??_

Unga business work ah simplify pana: *Mobile App, Website, CRM, ERP, AI Integration, etc* venuma??
Naanga _customized_ ah pani tharuvom, along with *domain & hosting setup, with annual maintenance plans.*

> Starting from just ₹10,000. Fully yours, no subscription.

Check our experience at https://k2ms.in

Thank you for taking your time to read this!

Regards,
K2M Services
Urapakkam`;
        let cleanPhone = phone.replace(/\D/g, '');
        if (cleanPhone.startsWith('0')) cleanPhone = '91' + cleanPhone.slice(1);
        else if (cleanPhone.length === 10) cleanPhone = '91' + cleanPhone;
        return `https://wa.me/${cleanPhone.slice(-12)}?text=${encodeURIComponent(text)}`;
    }
</script>

<svelte:head>
    <title>CRM | K2MS</title>
</svelte:head>

{#if !data.authed}
<div class="min-h-screen flex items-center justify-center p-4 bg-gray-50">
    <div class="bg-white border-4 border-black rounded-3xl p-8 max-w-sm w-full shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] text-center">
        <h1 class="text-2xl font-black uppercase tracking-tighter mb-2">Restricted Access</h1>
        <p class="text-gray-600 font-bold mb-6">Enter CRM PIN to continue</p>
        
        <form method="POST" action="?/login" use:enhance>
            <input 
                type="password" 
                name="pin" 
                pattern="[0-9]*" 
                inputmode="numeric"
                maxlength="4"
                oninput={(e) => {
                    if (e.currentTarget.value.length === 4) {
                        e.currentTarget.form?.requestSubmit();
                    }
                }}
                class="w-full text-center text-2xl font-black tracking-widest border-4 border-black rounded-xl p-4 focus:outline-none focus:ring-4 focus:ring-yellow-200"
                placeholder="••••"
                required
                autofocus
            />
        </form>
    </div>
</div>
{:else}
<div class="max-w-6xl mx-auto p-4 pb-24 space-y-6">
    <header class="flex items-center justify-between py-4">
        <h1 class="text-4xl font-black uppercase tracking-tighter" style="color: var(--color-brand)">
            K2MS <span class="text-black">CRM</span>
        </h1>
        <div class="bg-black text-white px-4 py-1.5 rounded-full text-sm font-bold shadow-[2px_2px_0px_0px_var(--color-brand)]">
            {data.leads.main.length + data.leads.call.length} Leads
        </div>
    </header>

    <!-- Tabs -->
    <div class="flex flex-col sm:flex-row border-4 border-black rounded-xl overflow-hidden shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] bg-white font-bold text-lg">
        <button 
            class="flex-1 py-3 text-center border-b-4 sm:border-b-0 sm:border-r-4 border-black transition-colors duration-200 {activeTab === 'main' ? 'bg-[var(--color-brand-light)] text-black' : 'hover:bg-gray-100'}"
            onclick={() => activeTab = 'main'}
        >
            Main Inbox ({data.leads.main.length})
        </button>
        <button 
            class="flex-1 py-3 text-center transition-colors duration-200 {activeTab === 'call' ? 'bg-[var(--color-call)] text-white' : 'hover:bg-gray-100'}"
            onclick={() => activeTab = 'call'}
        >
            Follow Ups ({data.leads.call.length})
        </button>
    </div>

    <!-- Feed -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        {#each activeTab === 'main' ? data.leads.main : data.leads.call as lead (lead.id)}
            <!-- DISPLAY CARD -->
            <div class="relative overflow-hidden group border-4 border-black rounded-2xl p-5 bg-white shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:translate-y-1 hover:translate-x-1 transition-all flex flex-col h-full">
                {#if submittingId === lead.id}
                    <div class="absolute inset-0 bg-white/60 backdrop-blur-[2px] z-30 flex flex-col items-center justify-center">
                        <div class="w-10 h-10 border-4 border-black border-t-transparent rounded-full animate-spin mb-2"></div>
                        <span class="font-black text-sm uppercase">Updating...</span>
                    </div>
                {/if}
                <div class="flex justify-between items-start mb-4 gap-2">
                    <div class="flex items-start gap-2">
                        <h2 class="text-2xl font-bold leading-tight">{lead.business}</h2>
                        {#if lead.stage === 'main'}
                            <form method="POST" action="?/deleteLead" use:enhance={() => {
                                submittingId = lead.id;
                                return async ({ update }) => {
                                    await update({ reset: false });
                                    submittingId = null;
                                };
                            }}>
                                <input type="hidden" name="id" value={lead.id} />
                                <button 
                                    type="submit" 
                                    class="mt-1 text-red-500 hover:text-red-700 hover:bg-red-50 p-1 rounded transition-colors active:scale-95" 
                                    title="Delete Lead"
                                    onclick={(e) => !confirm('Are you sure you want to delete this lead?') && e.preventDefault()}
                                >
                                    <Trash2 size={20} />
                                </button>
                            </form>
                        {/if}
                    </div>
                    
                    {#if lead.stage === 'main'}
                    <!-- FUNKY EDITABLE STATUS PILL -->
                    <div class="relative">
                        <button 
                            type="button"
                            onclick={() => openDropdown = openDropdown === lead.id ? null : lead.id}
                            class="px-3 py-1 text-xs font-bold uppercase border-2 border-black rounded-full {getStatusColor(lead.status)} text-center whitespace-nowrap shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:translate-y-[1px] hover:translate-x-[1px] hover:shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] transition-all flex items-center gap-1 active:scale-95"
                        >
                            {lead.status || 'Pending'}
                            <ChevronDown size={14} class="opacity-70" />
                        </button>
                        
                        {#if openDropdown === lead.id}
                            <div class="absolute z-20 right-0 mt-2 w-36 bg-white border-4 border-black rounded-xl shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] overflow-hidden flex flex-col">
                                {#each ['Pending', 'Contacted', 'Interested', 'Converted', 'Rejected'] as s}
                                    <form method="POST" action="?/updateStatus" use:enhance={() => {
                                        submittingId = lead.id;
                                        return async ({ update }) => {
                                            await update({ reset: false });
                                            submittingId = null;
                                            openDropdown = null;
                                        };
                                    }}>
                                        <input type="hidden" name="id" value={lead.id} />
                                        <input type="hidden" name="status" value={s} />
                                        <button 
                                            type="submit" 
                                            class="w-full text-left px-4 py-3 text-xs font-bold uppercase border-b-2 border-black last:border-b-0 hover:bg-gray-100 {lead.status === s ? getStatusColor(s) : ''}"
                                        >
                                            {s}
                                        </button>
                                    </form>
                                {/each}
                            </div>
                            
                            <!-- Invisible Backdrop -->
                            <div 
                                class="fixed inset-0 z-10" 
                                onclick={() => openDropdown = null}
                                role="button" tabindex="0" onkeypress={(e) => e.key === 'Escape' && (openDropdown = null)}
                            ></div>
                        {/if}
                    </div>
                    {/if}
                </div>
                
                {#if lead.remarks}
                    <div class="bg-gray-50 border-2 border-black border-dashed rounded-lg p-3 mb-4 text-sm font-medium whitespace-pre-wrap">
                        <span class="text-gray-500 uppercase text-xs font-bold block mb-1">Remarks / Needs</span>{lead.remarks}
                    </div>
                {/if}

                <div class="flex gap-2 mt-auto pt-4 border-t-2 border-black">
                    {#if lead.stage === 'main'}
                        {#if lead.phone}
                            <a href="{lead.pitch_url || getPitchUrl(lead.phone, lead.business)}" target="_blank" rel="noopener noreferrer" 
                               class="flex-1 flex justify-center items-center gap-1 sm:gap-2 bg-[#25D366] text-white border-2 border-black rounded-lg px-1 sm:px-2 py-2 font-bold hover:bg-[#1da851] active:scale-95 transition-transform shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] overflow-hidden">
                                <MessageCircle size={18} class="shrink-0" /> <span class="truncate hidden min-[360px]:inline">Pitch</span>
                            </a>
                        {:else}
                            <button disabled class="flex-1 flex justify-center items-center gap-1 sm:gap-2 bg-gray-100 text-gray-400 border-2 border-dashed border-gray-300 rounded-lg px-1 sm:px-2 py-2 font-bold cursor-not-allowed overflow-hidden">
                                <MessageCircle size={18} class="shrink-0" /> <span class="truncate hidden min-[360px]:inline">Pitch</span>
                            </button>
                        {/if}

                        {#if lead.idea_url}
                            <a href="{lead.idea_url}" target="_blank" rel="noopener noreferrer" 
                               class="flex-1 flex justify-center items-center gap-1 sm:gap-2 bg-[#00a884] text-white border-2 border-black rounded-lg px-1 sm:px-2 py-2 font-bold hover:bg-[#008f6f] active:scale-95 transition-transform shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] overflow-hidden">
                                <MessageCircle size={18} class="shrink-0" /> <span class="truncate hidden min-[360px]:inline">Idea</span>
                            </a>
                        {:else}
                            <button disabled class="flex-1 flex justify-center items-center gap-1 sm:gap-2 bg-gray-100 text-gray-400 border-2 border-dashed border-gray-300 rounded-lg px-1 sm:px-2 py-2 font-bold cursor-not-allowed overflow-hidden">
                                <MessageCircle size={18} class="shrink-0" /> <span class="truncate hidden min-[360px]:inline">Idea</span>
                            </button>
                        {/if}
                        
                        {#if lead.website}
                            <a href="{lead.website}" target="_blank" class="flex-none flex justify-center items-center p-2 border-2 border-black rounded-lg hover:bg-gray-100 bg-white shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] active:scale-95 transition-transform ml-auto">
                                <Globe size={18} />
                            </a>
                        {:else}
                            <button disabled class="flex-none flex justify-center items-center p-2 border-2 border-dashed border-gray-300 rounded-lg text-gray-400 bg-gray-100 ml-auto cursor-not-allowed">
                                <Globe size={18} />
                            </button>
                        {/if}
                    {:else if lead.stage === 'call'}
                        {#if lead.phone}
                            <button type="button" onclick={() => scriptModalLead = lead}
                               class="flex-none w-12 sm:w-14 flex justify-center items-center bg-[#3b82f6] text-white border-2 border-black rounded-lg py-2 font-bold hover:bg-[#2563eb] active:scale-95 transition-transform shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] overflow-hidden">
                                <Phone size={20} class="shrink-0" />
                            </button>
                        {:else}
                            <button disabled class="flex-none w-12 sm:w-14 flex justify-center items-center bg-gray-100 text-gray-400 border-2 border-dashed border-gray-300 rounded-lg py-2 font-bold cursor-not-allowed overflow-hidden">
                                <Phone size={20} class="shrink-0" />
                            </button>
                        {/if}

                        <form method="POST" action="?/moveLead" use:enhance={({ submitter }) => {
                            submittingId = lead.id;
                            const statusVal = submitter?.getAttribute('value');
                            return async ({ result, update }) => {
                                await update({ reset: false });
                                submittingId = null;
                                if (result.type === 'success' && statusVal === 'Interested' && lead.idea_url) {
                                    window.open(lead.idea_url, '_blank');
                                }
                            };
                        }} class="flex-1 flex gap-2 w-full">
                            <input type="hidden" name="id" value={lead.id} />
                            <button type="submit" name="status" value="Interested" class="flex-1 bg-[#25D366] text-white border-2 border-black rounded-lg py-2 font-black uppercase text-sm sm:text-base hover:bg-[#1da851] active:scale-95 transition-transform shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] overflow-hidden text-ellipsis whitespace-nowrap">
                                Interested
                            </button>
                            <button type="submit" name="status" value="Rejected" class="flex-1 bg-red-500 text-white border-2 border-black rounded-lg py-2 font-black uppercase text-sm sm:text-base hover:bg-red-600 active:scale-95 transition-transform shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] overflow-hidden text-ellipsis whitespace-nowrap">
                                Reject
                            </button>
                        </form>
                    {/if}
                </div>
            </div>
        {/each}
        
        {#if (activeTab === 'main' ? data.leads.main : data.leads.call).length === 0}
            <div class="p-12 text-center border-4 border-black border-dashed rounded-2xl bg-white/50 col-span-1 md:col-span-2">
                <p class="text-xl font-bold text-gray-500">No leads in this view!</p>
            </div>
        {/if}
    </div>
</div>

{#if scriptModalLead}
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm overflow-y-auto" onclick={() => scriptModalLead = null} role="button" tabindex="0" onkeypress={(e) => e.key === 'Escape' && (scriptModalLead = null)}>
        <div class="bg-white border-4 border-black rounded-3xl p-6 md:p-8 max-w-lg w-full shadow-[12px_12px_0px_0px_rgba(0,0,0,1)] relative my-auto" onclick={(e) => e.stopPropagation()} role="document">
            <button onclick={() => scriptModalLead = null} class="absolute top-4 right-4 text-gray-400 hover:text-black font-black bg-gray-100 hover:bg-gray-200 rounded-full w-8 h-8 flex items-center justify-center transition-colors">✕</button>
            
            <h3 class="text-2xl font-black uppercase border-b-4 border-black pb-4 mb-6 tracking-tight">Cold Call Script</h3>
            
            <div class="space-y-6 text-lg font-bold text-gray-800">
                <div class="p-4 bg-blue-50 border-4 border-black rounded-xl shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                    <p class="mb-2">Hello, is this <span class="bg-yellow-200 px-1 border border-black rounded uppercase text-black">{scriptModalLead.business}</span>?</p>
                    <p>This is Sujithra from K2M Software Services.</p>
                </div>
                
                <div class="p-4 bg-purple-50 border-4 border-black rounded-xl shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                    <p>Unga business ku <span class="bg-yellow-200 px-1 border border-black rounded text-black">{scriptModalLead.remarks || 'Digital Marketing'}</span> help thevaya? Price pathi laam nenga rombo worry pana venam.</p>
                </div>
                
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-8 pt-6 border-t-4 border-black border-dashed">
                    <div class="p-4 bg-green-100 border-4 border-black rounded-xl shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                        <h4 class="font-black text-green-800 flex items-center gap-2 mb-2 text-xl uppercase">✅ Yes</h4>
                        <p class="text-sm font-semibold text-green-900 leading-relaxed">Ok sir, our technical team will contact you soon for more details, thank you!</p>
                    </div>
                    
                    <div class="p-4 bg-red-100 border-4 border-black rounded-xl shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                        <h4 class="font-black text-red-800 flex items-center gap-2 mb-2 text-xl uppercase">❌ No</h4>
                        <p class="text-sm font-semibold text-red-900 leading-relaxed">Ok sir, future la requirements vantha do contact us, thank you!</p>
                    </div>
                </div>
            </div>
            
            <div class="mt-8 flex gap-4">
                <button onclick={() => scriptModalLead = null} class="flex-1 bg-white border-4 border-black text-black font-black uppercase py-4 rounded-xl shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:bg-gray-100 active:scale-95 transition-transform">Close</button>
                <a href="tel:{scriptModalLead.phone}" class="flex-[2] bg-[#3b82f6] border-4 border-black text-white flex justify-center items-center gap-2 font-black uppercase py-4 rounded-xl shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:bg-[#2563eb] active:scale-95 transition-transform">
                    <Phone size={20} /> Dial Now
                </a>
            </div>
        </div>
    </div>
{/if}
{/if}
