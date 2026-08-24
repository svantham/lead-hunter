<script lang="ts">
    import { enhance } from '$app/forms';
    import MessageCircle from 'lucide-svelte/icons/message-circle';
    import Phone from 'lucide-svelte/icons/phone';
    import Globe from 'lucide-svelte/icons/globe';
    import ChevronDown from 'lucide-svelte/icons/chevron-down';
    let { data } = $props();
    
    let activeTab = $state<'main' | 'call'>('main');
    let openDropdown = $state<number | null>(null);
    
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
        const text = `Hi ${business} Team,\n\nI'm reaching out from K2M Services. We build custom software solutions (Mobile App, Website, CRM, ERP, AI Integration, etc.) to help businesses like yours automate workflows and scale efficiently.\n\nWould you be open to a quick chat to see if we can help streamline your operations?\n\nCheck out our work here: https://k2ms.in`;
        let cleanPhone = phone.replace(/\D/g, '');
        if (cleanPhone.startsWith('0')) cleanPhone = '91' + cleanPhone.slice(1);
        else if (cleanPhone.length === 10) cleanPhone = '91' + cleanPhone;
        return `https://wa.me/${cleanPhone.slice(-12)}?text=${encodeURIComponent(text)}`;
    }
</script>

<svelte:head>
    <title>CRM | K2MS</title>
</svelte:head>

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
            <div class="group border-4 border-black rounded-2xl p-5 bg-white shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:translate-y-1 hover:translate-x-1 transition-all flex flex-col h-full">
                <div class="flex justify-between items-start mb-4 gap-2">
                    <div>
                        <h2 class="text-2xl font-bold leading-tight">{lead.business}</h2>
                    </div>
                    
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
                                {#each ['Pending', 'Contacted', 'Interested', 'Converted', 'Rejected'].filter(s => !(lead.stage === 'call' && s === 'Contacted')) as s}
                                    <form method="POST" action="?/updateStatus" use:enhance={() => {
                                        return async ({ update }) => {
                                            await update({ reset: false });
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
                </div>
                
                {#if lead.remarks}
                <div class="bg-gray-50 border-2 border-black border-dashed rounded-lg p-3 mb-4 text-sm font-medium whitespace-pre-wrap">
                    <span class="text-gray-500 uppercase text-xs font-bold block mb-1">Remarks / Needs</span>{lead.remarks}
                </div>
                {/if}

                <div class="flex gap-2 mt-auto pt-4 border-t-2 border-black">
                    {#if lead.phone}
                        <a href="tel:{lead.phone}" 
                           class="flex-1 flex justify-center items-center gap-1 sm:gap-2 bg-[#3b82f6] text-white border-2 border-black rounded-lg px-2 sm:px-4 py-2 font-bold hover:bg-[#2563eb] active:scale-95 transition-transform shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] overflow-hidden">
                            <Phone size={18} class="shrink-0" /> <span class="truncate hidden min-[360px]:inline">Call</span>
                        </a>
                    {:else}
                        <button disabled class="flex-1 flex justify-center items-center gap-1 sm:gap-2 bg-gray-100 text-gray-400 border-2 border-dashed border-gray-300 rounded-lg px-2 sm:px-4 py-2 font-bold cursor-not-allowed overflow-hidden">
                            <Phone size={18} class="shrink-0" /> <span class="truncate hidden min-[360px]:inline">Call</span>
                        </button>
                    {/if}

                    {#if lead.stage === 'main'}
                        {#if lead.phone}
                            <a href="{getPitchUrl(lead.phone, lead.business)}" target="_blank" rel="noopener noreferrer" 
                               class="flex-1 flex justify-center items-center gap-1 sm:gap-2 bg-[#25D366] text-white border-2 border-black rounded-lg px-1 sm:px-2 py-2 font-bold hover:bg-[#1da851] active:scale-95 transition-transform shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] overflow-hidden">
                                <MessageCircle size={18} class="shrink-0" /> <span class="truncate hidden min-[360px]:inline">Pitch</span>
                            </a>
                        {:else}
                            <button disabled class="flex-1 flex justify-center items-center gap-1 sm:gap-2 bg-gray-100 text-gray-400 border-2 border-dashed border-gray-300 rounded-lg px-1 sm:px-2 py-2 font-bold cursor-not-allowed overflow-hidden">
                                <MessageCircle size={18} class="shrink-0" /> <span class="truncate hidden min-[360px]:inline">Pitch</span>
                            </button>
                        {/if}
                    {/if}

                    {#if lead.idea_url}
                        <a href="{lead.idea_url}" target="_blank" rel="noopener noreferrer" 
                           class="flex-1 flex justify-center items-center gap-1 sm:gap-2 bg-[#00a884] text-white border-2 border-black rounded-lg px-1 sm:px-2 py-2 font-bold hover:bg-[#008f6f] active:scale-95 transition-transform shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] overflow-hidden">
                            <MessageCircle size={18} class="shrink-0" /> <span class="truncate hidden min-[360px]:inline">{lead.stage === 'main' ? 'Idea' : 'WhatsApp'}</span>
                        </a>
                    {:else}
                        <button disabled class="flex-1 flex justify-center items-center gap-1 sm:gap-2 bg-gray-100 text-gray-400 border-2 border-dashed border-gray-300 rounded-lg px-1 sm:px-2 py-2 font-bold cursor-not-allowed overflow-hidden">
                            <MessageCircle size={18} class="shrink-0" /> <span class="truncate hidden min-[360px]:inline">{lead.stage === 'main' ? 'Idea' : 'WhatsApp'}</span>
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
