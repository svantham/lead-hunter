<script lang="ts">
    import { enhance } from "$app/forms";
    import MessageCircle from "lucide-svelte/icons/message-circle";
    import Phone from "lucide-svelte/icons/phone";
    import ChevronDown from "lucide-svelte/icons/chevron-down";
    import Trash2 from "lucide-svelte/icons/trash-2";
    import ArrowRight from "lucide-svelte/icons/arrow-right";
    import Plus from "lucide-svelte/icons/plus";
    import IndianRupee from "lucide-svelte/icons/indian-rupee";
    import TrendingUp from "lucide-svelte/icons/trending-up";
    import Users from "lucide-svelte/icons/users";
    import Briefcase from "lucide-svelte/icons/briefcase";

    let { data } = $props();

    let activeTab = $state<"main" | "call" | "revenue">("main");
    let selectedSegment = $state<string>("regular");
    let selectedStatusFilter = $state<string>("Pending");
    let selectedRevenueTypeFilter = $state<string>("all");

    const filterStatuses = [
        "Pending",
        "Contacted",
        "Interested",
        "Converted",
        "Rejected",
    ];

    // Dynamic segments derived from all leads
    let availableSegments = $derived.by(() => {
        const allLeads = [
            ...(data.leads.main || []),
            ...(data.leads.call || []),
        ];
        const segs = new Set<string>();
        for (const l of allLeads) {
            segs.add((l.segment || "regular").toLowerCase());
        }
        // Ensure "regular" is always an option even if no leads exist yet
        if (segs.size === 0) segs.add("regular");
        return Array.from(segs).sort();
    });

    // Leads filtered by active segment
    let segmentFilteredMain = $derived(
        data.leads.main.filter(
            (l: any) =>
                (l.segment || "regular").toLowerCase() === selectedSegment,
        ),
    );

    let currentLeads = $derived(
        activeTab === "main" ? segmentFilteredMain : data.leads.call,
    );

    let filteredLeads = $derived(
        activeTab === "main"
            ? currentLeads.filter(
                  (lead: any) => lead.status === selectedStatusFilter,
              )
            : currentLeads,
    );

    let statusCounts = $derived.by(() => {
        const base = segmentFilteredMain;
        const counts: Record<string, number> = {
            Pending: 0,
            Contacted: 0,
            Interested: 0,
            Converted: 0,
            Rejected: 0,
        };
        for (const lead of base) {
            if (counts[lead.status] !== undefined) {
                counts[lead.status]++;
            } else {
                counts[lead.status] = 1;
            }
        }
        return counts;
    });

    // Revenue tracking derivations
    let revenueRecords = $derived(data.revenueRecords || []);
    let currentMonth = new Date().toISOString().slice(0, 7);

    let totalRevenue = $derived.by(() => {
        return revenueRecords.reduce(
            (sum: number, r: any) => sum + (Number(r.amount) || 0),
            0,
        );
    });

    let monthlyRecurring = $derived.by(() => {
        return revenueRecords
            .filter(
                (r: any) =>
                    r.type === "recurring_partner" && r.period === currentMonth,
            )
            .reduce((sum: number, r: any) => sum + (Number(r.amount) || 0), 0);
    });

    let totalReferralFees = $derived.by(() => {
        return revenueRecords
            .filter((r: any) => r.type === "referral_fee")
            .reduce((sum: number, r: any) => sum + (Number(r.amount) || 0), 0);
    });

    let totalOneTime = $derived.by(() => {
        return revenueRecords
            .filter((r: any) => r.type === "one_time")
            .reduce((sum: number, r: any) => sum + (Number(r.amount) || 0), 0);
    });

    let filteredRevenueRecords = $derived(
        selectedRevenueTypeFilter === "all"
            ? revenueRecords
            : revenueRecords.filter(
                  (r: any) => r.type === selectedRevenueTypeFilter,
              ),
    );

    let openDropdown = $state<number | null>(null);
    let scriptModalLead = $state<any>(null);
    let submittingId = $state<number | null>(null);
    let revenueModalLead = $state<any>(null);
    let showAddLeadModal = $state(false);
    let newLeadSegment = $state("regular");

    $effect(() => {
        if (showAddLeadModal) {
            newLeadSegment = selectedSegment;
        }
    });
    let showAddRevenueModal = $state(false);

    // Status styling
    const statusColors: Record<string, string> = {
        Pending: "bg-yellow-200 text-yellow-900 border-yellow-900",
        Contacted: "bg-blue-200 text-blue-900 border-blue-900",
        Interested: "bg-green-200 text-green-900 border-green-900",
        Converted: "bg-fuchsia-200 text-fuchsia-900 border-fuchsia-900",
        Rejected: "bg-red-200 text-red-900 border-red-900",
    };

    function getStatusColor(status: string) {
        return (
            statusColors[status] || "bg-gray-200 text-gray-900 border-gray-900"
        );
    }

    function getWebsiteUrl(website: string, business: string) {
        if (
            website &&
            website.toLowerCase() !== "view" &&
            website.startsWith("http")
        ) {
            return website;
        }
        return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(business)}`;
    }

    function getPitchUrl(phone: string, business: string) {
        if (!phone) return "";
        const text = `*${business}*,

_Innum Excel use panitu irukingala?  Unga business work ah automate pananuma??_

Unga business work ah simplify pana: *Mobile App, Website, CRM, ERP, AI Integration, etc* venuma??
Naanga _customized_ ah pani tharuvom, along with *domain & hosting setup, with annual maintenance plans.*

> Starting from just ₹10,000. Fully yours, no subscription.

Check our experience at https://svantham.in/tailored

Regards,
Svantham Software
Urapakkam`;
        let cleanPhone = phone.replace(/\D/g, "");
        if (cleanPhone.startsWith("0")) cleanPhone = "91" + cleanPhone.slice(1);
        else if (cleanPhone.length === 10) cleanPhone = "91" + cleanPhone;
        return `https://wa.me/${cleanPhone.slice(-12)}?text=${encodeURIComponent(text)}`;
    }

    function formatCurrency(amount: number | string) {
        const num = Number(amount) || 0;
        return "₹" + num.toLocaleString("en-IN");
    }
</script>

<svelte:head>
    <title>CRM | Svantham</title>
</svelte:head>

{#if !data.authed}
    <div class="min-h-screen flex items-center justify-center p-4 bg-gray-50">
        <div
            class="bg-white border-4 border-black rounded-3xl p-8 max-w-sm w-full shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] text-center"
        >
            <h1 class="text-2xl font-black uppercase tracking-tighter mb-2">
                Restricted Access
            </h1>
            <p class="text-gray-600 font-bold mb-6">
                Enter CRM PIN to continue
            </p>
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
        <!-- Top Header -->
        <header class="flex items-center justify-between py-4">
            <h1
                class="text-4xl font-black uppercase tracking-tighter"
                style="color: var(--color-brand)"
            >
                Svantham <span class="text-black">CRM</span>
            </h1>
            <div class="flex items-center gap-3">
                {#if activeTab === "main"}
                    <button
                        type="button"
                        onclick={() => (showAddLeadModal = true)}
                        class="bg-white border-2 border-black px-3 py-1.5 rounded-full text-sm font-bold shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:bg-gray-50 active:scale-95 flex items-center gap-1"
                    >
                        <Plus size={16} /> New Lead
                    </button>
                {:else if activeTab === "revenue"}
                    <button
                        type="button"
                        onclick={() => (showAddRevenueModal = true)}
                        class="bg-green-500 text-white border-2 border-black px-3 py-1.5 rounded-full text-sm font-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:bg-green-600 active:scale-95 flex items-center gap-1 uppercase"
                    >
                        <Plus size={16} /> Log Revenue
                    </button>
                {/if}
                <div
                    class="bg-black text-white px-4 py-1.5 rounded-full text-sm font-bold shadow-[2px_2px_0px_0px_var(--color-brand)]"
                >
                    {data.leads.main.length + data.leads.call.length} Leads
                </div>
            </div>
        </header>

        <!-- Root-Level Segment Switch -->
        {#if activeTab === "main"}
            <div
                class="bg-gray-100 p-2 border-2 border-black rounded-2xl flex flex-wrap items-center gap-2 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]"
            >
                <span
                    class="text-xs font-black uppercase tracking-wider text-gray-500 ml-2 mr-1"
                    >Segment:</span
                >
                {#each availableSegments as seg}
                    <button
                        type="button"
                        onclick={() => (selectedSegment = seg)}
                        class="px-3 py-1 text-xs font-black uppercase rounded-lg border-2 border-black transition-all shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] hover:translate-y-0.5 hover:translate-x-0.5 hover:shadow-none {selectedSegment ===
                        seg
                            ? 'bg-black text-white'
                            : 'bg-white text-black hover:bg-gray-50'}"
                    >
                        {seg}
                    </button>
                {/each}
            </div>
        {/if}

        <!-- 3 Primary Navigation Tabs -->
        <div
            class="flex flex-col sm:flex-row border-4 border-black rounded-xl overflow-hidden shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] bg-white font-bold text-lg"
        >
            <button
                class="flex-1 py-3 text-center border-b-4 sm:border-b-0 sm:border-r-4 border-black transition-colors duration-200 {activeTab ===
                'main'
                    ? 'bg-[var(--color-brand-light)] text-black'
                    : 'hover:bg-gray-100'}"
                onclick={() => (activeTab = "main")}
            >
                Main Inbox ({segmentFilteredMain.length})
            </button>
            <button
                class="flex-1 py-3 text-center border-b-4 sm:border-b-0 sm:border-r-4 border-black transition-colors duration-200 {activeTab ===
                'call'
                    ? 'bg-[var(--color-call)] text-white'
                    : 'hover:bg-gray-100'}"
                onclick={() => (activeTab = "call")}
            >
                Follow Ups ({data.leads.call.length})
            </button>
            <button
                class="flex-1 py-3 text-center transition-colors duration-200 {activeTab ===
                'revenue'
                    ? 'bg-green-400 text-black'
                    : 'hover:bg-gray-100'}"
                onclick={() => (activeTab = "revenue")}
            >
                Revenue & Partnerships ({formatCurrency(totalRevenue)})
            </button>
        </div>

        <!-- ========================================================= -->
        <!-- REVENUE & PARTNERSHIPS VIEW                               -->
        <!-- ========================================================= -->
        {#if activeTab === "revenue"}
            <div class="space-y-6">
                <!-- 4 High-Level Metrics -->
                <div
                    class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
                >
                    <div
                        class="bg-white border-4 border-black rounded-2xl p-5 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] flex flex-col justify-between"
                    >
                        <div class="flex justify-between items-start mb-2">
                            <span
                                class="text-xs font-black uppercase text-gray-500"
                                >Total Revenue</span
                            >
                            <div
                                class="p-2 bg-green-100 rounded-lg border border-black"
                            >
                                <IndianRupee size={20} class="text-green-700" />
                            </div>
                        </div>
                        <div class="text-3xl font-black text-green-700">
                            {formatCurrency(totalRevenue)}
                        </div>
                        <div class="text-xs font-bold text-gray-500 mt-2">
                            All time collected
                        </div>
                    </div>

                    <div
                        class="bg-white border-4 border-black rounded-2xl p-5 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] flex flex-col justify-between"
                    >
                        <div class="flex justify-between items-start mb-2">
                            <span
                                class="text-xs font-black uppercase text-gray-500"
                                >MRR (This Month)</span
                            >
                            <div
                                class="p-2 bg-blue-100 rounded-lg border border-black"
                            >
                                <TrendingUp size={20} class="text-blue-700" />
                            </div>
                        </div>
                        <div class="text-3xl font-black text-blue-700">
                            {formatCurrency(monthlyRecurring)}
                        </div>
                        <div class="text-xs font-bold text-gray-500 mt-2">
                            Agency white-label retainers
                        </div>
                    </div>

                    <div
                        class="bg-white border-4 border-black rounded-2xl p-5 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] flex flex-col justify-between"
                    >
                        <div class="flex justify-between items-start mb-2">
                            <span
                                class="text-xs font-black uppercase text-gray-500"
                                >Referral Commissions</span
                            >
                            <div
                                class="p-2 bg-yellow-100 rounded-lg border border-black"
                            >
                                <Users size={20} class="text-yellow-800" />
                            </div>
                        </div>
                        <div class="text-3xl font-black text-yellow-800">
                            {formatCurrency(totalReferralFees)}
                        </div>
                        <div class="text-xs font-bold text-gray-500 mt-2">
                            CA partner referrals
                        </div>
                    </div>

                    <div
                        class="bg-white border-4 border-black rounded-2xl p-5 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] flex flex-col justify-between"
                    >
                        <div class="flex justify-between items-start mb-2">
                            <span
                                class="text-xs font-black uppercase text-gray-500"
                                >One-Time Projects</span
                            >
                            <div
                                class="p-2 bg-purple-100 rounded-lg border border-black"
                            >
                                <Briefcase size={20} class="text-purple-700" />
                            </div>
                        </div>
                        <div class="text-3xl font-black text-purple-700">
                            {formatCurrency(totalOneTime)}
                        </div>
                        <div class="text-xs font-bold text-gray-500 mt-2">
                            Direct client builds
                        </div>
                    </div>
                </div>

                <!-- Revenue Stream Ledger -->
                <div
                    class="bg-white border-4 border-black rounded-2xl p-6 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]"
                >
                    <div
                        class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 pb-4 border-b-2 border-black"
                    >
                        <div>
                            <h2
                                class="text-2xl font-black uppercase tracking-tight"
                            >
                                Revenue & Partnership Ledger
                            </h2>
                            <p class="text-sm font-bold text-gray-600">
                                Track monthly retainers, client payments, and
                                referral fee allocations
                            </p>
                        </div>
                        <!-- Revenue Type Filters -->
                        <div class="flex flex-wrap gap-2">
                            {#each [{ id: "all", label: "All" }, { id: "recurring_partner", label: "Agency Retainers" }, { id: "referral_fee", label: "CA Referral Fees" }, { id: "one_time", label: "One-Time" }] as f}
                                <button
                                    type="button"
                                    onclick={() =>
                                        (selectedRevenueTypeFilter = f.id)}
                                    class="px-3 py-1 text-xs font-black uppercase rounded-full border-2 border-black transition-all {selectedRevenueTypeFilter ===
                                    f.id
                                        ? 'bg-black text-white'
                                        : 'bg-gray-100 hover:bg-gray-200 text-black'}"
                                >
                                    {f.label}
                                </button>
                            {/each}
                        </div>
                    </div>

                    {#if filteredRevenueRecords.length === 0}
                        <div
                            class="text-center py-12 border-2 border-dashed border-gray-300 rounded-xl"
                        >
                            <p class="text-gray-500 font-bold">
                                No revenue records logged yet.
                            </p>
                            <button
                                type="button"
                                onclick={() => (showAddRevenueModal = true)}
                                class="mt-3 bg-green-500 text-white font-black px-4 py-2 border-2 border-black rounded-xl shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:bg-green-600 text-sm uppercase"
                            >
                                + Log First Revenue
                            </button>
                        </div>
                    {:else}
                        <div class="overflow-x-auto">
                            <table class="w-full text-left border-collapse">
                                <thead>
                                    <tr
                                        class="border-b-2 border-black text-xs font-black uppercase text-gray-500"
                                    >
                                        <th class="py-3 px-3">Period</th>
                                        <th class="py-3 px-3"
                                            >Business / Partner</th
                                        >
                                        <th class="py-3 px-3">Type</th>
                                        <th class="py-3 px-3">Notes</th>
                                        <th class="py-3 px-3 text-right"
                                            >Amount</th
                                        >
                                        <th class="py-3 px-3 text-center"
                                            >Action</th
                                        >
                                    </tr>
                                </thead>
                                <tbody
                                    class="divide-y-2 divide-gray-100 font-bold text-sm"
                                >
                                    {#each filteredRevenueRecords as r (r.id)}
                                        <tr
                                            class="hover:bg-gray-50 transition-colors"
                                        >
                                            <td
                                                class="py-3 px-3 whitespace-nowrap"
                                            >
                                                <span
                                                    class="bg-gray-200 border border-black px-2 py-0.5 rounded text-xs font-black"
                                                    >{r.period}</span
                                                >
                                            </td>
                                            <td
                                                class="py-3 px-3 font-extrabold text-base"
                                                >{r.business}</td
                                            >
                                            <td
                                                class="py-3 px-3 whitespace-nowrap"
                                            >
                                                {#if r.type === "recurring_partner"}
                                                    <span
                                                        class="bg-blue-100 text-blue-800 border border-blue-800 px-2 py-0.5 rounded-full text-xs font-black uppercase"
                                                        >Agency Retainer</span
                                                    >
                                                {:else if r.type === "referral_fee"}
                                                    <span
                                                        class="bg-yellow-100 text-yellow-900 border border-yellow-800 px-2 py-0.5 rounded-full text-xs font-black uppercase"
                                                        >CA Referral Fee</span
                                                    >
                                                {:else}
                                                    <span
                                                        class="bg-purple-100 text-purple-900 border border-purple-800 px-2 py-0.5 rounded-full text-xs font-black uppercase"
                                                        >One-Time Build</span
                                                    >
                                                {/if}
                                            </td>
                                            <td
                                                class="py-3 px-3 text-gray-600 text-xs max-w-xs truncate"
                                                >{r.notes || "—"}</td
                                            >
                                            <td
                                                class="py-3 px-3 text-right font-black text-green-700 text-base whitespace-nowrap"
                                                >{formatCurrency(r.amount)}</td
                                            >
                                            <td class="py-3 px-3 text-center">
                                                <form
                                                    method="POST"
                                                    action="?/deleteRevenueRecord"
                                                    use:enhance
                                                    class="inline-block"
                                                >
                                                    <input
                                                        type="hidden"
                                                        name="id"
                                                        value={r.id}
                                                    />
                                                    <button
                                                        type="submit"
                                                        class="text-red-500 hover:text-red-700 p-1 rounded hover:bg-red-50 transition-colors"
                                                        title="Delete Record"
                                                        onclick={(e) =>
                                                            !confirm(
                                                                `Delete ${formatCurrency(r.amount)} revenue record for ${r.business}?`,
                                                            ) &&
                                                            e.preventDefault()}
                                                    >
                                                        <Trash2 size={16} />
                                                    </button>
                                                </form>
                                            </td>
                                        </tr>
                                    {/each}
                                </tbody>
                            </table>
                        </div>
                    {/if}
                </div>
            </div>

            <!-- ========================================================= -->
            <!-- MAIN & FOLLOW-UP FEED VIEW                                -->
            <!-- ========================================================= -->
        {:else}
            <!-- Status Pill Filters (Main Inbox & Follow Ups) -->
            {#if activeTab === "main"}
                <div class="flex flex-wrap gap-3 mb-6">
                    {#each filterStatuses as filterOption}
                        <button
                            onclick={() =>
                                (selectedStatusFilter = filterOption)}
                            class="px-4 py-2 font-black uppercase text-sm rounded-full border-2 border-black transition-all shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:translate-y-0.5 hover:translate-x-0.5 hover:shadow-none {selectedStatusFilter ===
                            filterOption
                                ? 'bg-black text-white'
                                : 'bg-white text-black'}"
                        >
                            {filterOption} ({statusCounts[filterOption] || 0})
                        </button>
                    {/each}
                </div>
            {/if}

            <!-- Feed Grid -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                {#each filteredLeads as lead (lead.id)}
                    <!-- DISPLAY CARD -->
                    <div
                        class="relative group border-4 border-black rounded-2xl p-5 bg-white shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:translate-y-1 hover:translate-x-1 transition-all flex flex-col h-full"
                    >
                        {#if submittingId === lead.id}
                            <div
                                class="absolute inset-0 bg-white/60 backdrop-blur-[2px] z-30 flex flex-col items-center justify-center rounded-xl"
                            >
                                <div
                                    class="w-10 h-10 border-4 border-black border-t-transparent rounded-full animate-spin mb-2"
                                ></div>
                                <span class="font-black text-sm uppercase"
                                    >Updating...</span
                                >
                            </div>
                        {/if}

                        <!-- Card Header -->
                        <div
                            class="flex flex-col sm:flex-row justify-between items-start mb-4 gap-3 sm:gap-2 w-full min-w-0"
                        >
                            <div
                                class="flex items-start gap-2 min-w-0 flex-1 w-full sm:w-auto"
                            >
                                <h2
                                    class="text-2xl font-bold leading-tight truncate min-w-0 flex-1"
                                >
                                    <a
                                        href={getWebsiteUrl(
                                            lead.website,
                                            lead.business,
                                        )}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        title={lead.business}
                                        class="hover:text-blue-600 transition-colors underline decoration-2 underline-offset-4 truncate block"
                                    >
                                        {lead.business}
                                    </a>
                                </h2>
                                {#if lead.segment && lead.segment !== "regular"}
                                    <span
                                        class="bg-black text-white px-2 py-0.5 rounded-full text-[10px] font-black uppercase mt-1.5 whitespace-nowrap"
                                    >
                                        {lead.segment}
                                    </span>
                                {/if}
                                {#if lead.stage === "main"}
                                    <form
                                        method="POST"
                                        action="?/deleteLead"
                                        use:enhance={() => {
                                            submittingId = lead.id;
                                            return async ({ update }) => {
                                                await update({ reset: false });
                                                submittingId = null;
                                            };
                                        }}
                                    >
                                        <input
                                            type="hidden"
                                            name="id"
                                            value={lead.id}
                                        />
                                        <button
                                            type="submit"
                                            class="mt-1 text-red-500 hover:text-red-700 hover:bg-red-50 p-1 rounded transition-colors active:scale-95"
                                            title="Delete Lead"
                                            onclick={(e) =>
                                                !confirm(
                                                    "Are you sure you want to delete this lead?",
                                                ) && e.preventDefault()}
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </form>
                                {/if}
                            </div>

                            {#if lead.stage === "main"}
                                <!-- Status Dropdown Pill -->
                                <div class="relative shrink-0">
                                    <button
                                        type="button"
                                        onclick={() =>
                                            (openDropdown =
                                                openDropdown === lead.id
                                                    ? null
                                                    : lead.id)}
                                        class="px-3 py-1 text-xs font-bold uppercase border-2 border-black rounded-full {getStatusColor(
                                            lead.status,
                                        )} text-center whitespace-nowrap shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:translate-y-[1px] hover:translate-x-[1px] hover:shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] transition-all flex items-center gap-1 active:scale-95"
                                    >
                                        {lead.status || "Pending"}
                                        <ChevronDown
                                            size={14}
                                            class="opacity-70"
                                        />
                                    </button>

                                    {#if openDropdown === lead.id}
                                        <div
                                            class="absolute z-20 left-0 sm:left-auto sm:right-0 mt-2 w-36 bg-white border-4 border-black rounded-xl shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] overflow-hidden flex flex-col"
                                        >
                                            {#each ["Pending", "Contacted", "Interested", "Converted", "Rejected"] as s}
                                                {#if s === "Converted"}
                                                    <button
                                                        type="button"
                                                        onclick={() => {
                                                            openDropdown = null;
                                                            revenueModalLead =
                                                                lead;
                                                        }}
                                                        class="w-full text-left px-4 py-3 text-xs font-bold uppercase border-b-2 border-black last:border-b-0 hover:bg-gray-100 {lead.status ===
                                                        s
                                                            ? getStatusColor(s)
                                                            : ''}"
                                                    >
                                                        {s}
                                                    </button>
                                                {:else}
                                                    <form
                                                        method="POST"
                                                        action="?/updateStatus"
                                                        use:enhance={() => {
                                                            submittingId =
                                                                lead.id;
                                                            return async ({
                                                                update,
                                                            }) => {
                                                                await update({
                                                                    reset: false,
                                                                });
                                                                submittingId =
                                                                    null;
                                                                openDropdown =
                                                                    null;
                                                            };
                                                        }}
                                                    >
                                                        <input
                                                            type="hidden"
                                                            name="id"
                                                            value={lead.id}
                                                        />
                                                        <input
                                                            type="hidden"
                                                            name="status"
                                                            value={s}
                                                        />
                                                        <button
                                                            type="submit"
                                                            class="w-full text-left px-4 py-3 text-xs font-bold uppercase border-b-2 border-black last:border-b-0 hover:bg-gray-100 {lead.status ===
                                                            s
                                                                ? getStatusColor(
                                                                      s,
                                                                  )
                                                                : ''}"
                                                        >
                                                            {s}
                                                        </button>
                                                    </form>
                                                {/if}
                                            {/each}
                                        </div>

                                        <div
                                            class="fixed inset-0 z-10"
                                            onclick={() =>
                                                (openDropdown = null)}
                                            role="button"
                                            tabindex="0"
                                            onkeypress={(e) =>
                                                e.key === "Escape" &&
                                                (openDropdown = null)}
                                        ></div>
                                    {/if}
                                </div>
                            {/if}
                        </div>

                        {#if lead.remarks && (!lead.segment || lead.segment === "regular")}
                            <div
                                class="bg-gray-50 border-2 border-black border-dashed rounded-lg p-3 mb-4 text-sm font-medium"
                            >
                                <div
                                    class="flex justify-between items-center mb-1"
                                >
                                    <span
                                        class="text-gray-500 uppercase text-xs font-bold"
                                        >Remarks / Needs</span
                                    >
                                </div>
                                <p
                                    class="line-clamp-2 h-10 text-gray-700 whitespace-pre-wrap"
                                    title={lead.remarks}
                                >
                                    {lead.remarks}
                                </p>
                            </div>
                        {/if}

                        <!-- Action Buttons -->
                        <div
                            class="flex gap-2 mt-auto pt-4 border-t-2 border-black"
                        >
                            {#if lead.stage === "main"}
                                {#if !lead.status || lead.status === "Pending"}
                                    {#if lead.phone}
                                        <a
                                            href={lead.pitch_url ||
                                                getPitchUrl(
                                                    lead.phone,
                                                    lead.business,
                                                )}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            class="flex-1 flex justify-center items-center gap-1 sm:gap-2 bg-[#25D366] text-white border-2 border-black rounded-lg px-1 sm:px-2 py-2 font-bold hover:bg-[#1da851] active:scale-95 transition-transform shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] overflow-hidden"
                                        >
                                            <MessageCircle
                                                size={18}
                                                class="shrink-0"
                                            />
                                            <span
                                                class="truncate hidden min-[360px]:inline"
                                                >Pitch</span
                                            >
                                        </a>
                                    {:else}
                                        <button
                                            disabled
                                            class="flex-1 flex justify-center items-center gap-1 sm:gap-2 bg-gray-100 text-gray-400 border-2 border-dashed border-gray-300 rounded-lg px-1 sm:px-2 py-2 font-bold cursor-not-allowed overflow-hidden"
                                        >
                                            <MessageCircle
                                                size={18}
                                                class="shrink-0"
                                            />
                                            <span
                                                class="truncate hidden min-[360px]:inline"
                                                >Pitch</span
                                            >
                                        </button>
                                    {/if}
                                {/if}

                                {#if lead.status === "Contacted" || lead.status === "Interested"}
                                    {#if lead.idea_url}
                                        <a
                                            href={lead.idea_url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            class="flex-1 flex justify-center items-center gap-1 sm:gap-2 bg-[#00a884] text-white border-2 border-black rounded-lg px-1 sm:px-2 py-2 font-bold hover:bg-[#008f6f] active:scale-95 transition-transform shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] overflow-hidden"
                                        >
                                            <MessageCircle
                                                size={18}
                                                class="shrink-0"
                                            />
                                            <span
                                                class="truncate hidden min-[360px]:inline"
                                                >Idea</span
                                            >
                                        </a>
                                    {:else}
                                        <button
                                            disabled
                                            class="flex-1 flex justify-center items-center gap-1 sm:gap-2 bg-gray-100 text-gray-400 border-2 border-dashed border-gray-300 rounded-lg px-1 sm:px-2 py-2 font-bold cursor-not-allowed overflow-hidden"
                                        >
                                            <MessageCircle
                                                size={18}
                                                class="shrink-0"
                                            />
                                            <span
                                                class="truncate hidden min-[360px]:inline"
                                                >Idea</span
                                            >
                                        </button>
                                    {/if}
                                {/if}

                                <div class="ml-auto flex gap-2">
                                    {#if !lead.status || lead.status === "Pending"}
                                        <form
                                            method="POST"
                                            action="?/moveToFollowUp"
                                            use:enhance={() => {
                                                submittingId = lead.id;
                                                return async ({ update }) => {
                                                    await update({
                                                        reset: false,
                                                    });
                                                    submittingId = null;
                                                };
                                            }}
                                            class="flex"
                                        >
                                            <input
                                                type="hidden"
                                                name="id"
                                                value={lead.id}
                                            />
                                            <button
                                                type="submit"
                                                class="flex justify-center items-center px-3 py-2 border-2 border-black rounded-lg hover:bg-yellow-200 bg-yellow-100 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] active:scale-95 transition-transform text-black font-bold h-full"
                                                title="Move to Follow-up"
                                            >
                                                <ArrowRight
                                                    size={18}
                                                    class="sm:mr-1"
                                                />
                                                <span class="hidden sm:inline"
                                                    >Follow-up</span
                                                >
                                            </button>
                                        </form>
                                    {/if}
                                </div>
                            {:else if lead.stage === "call"}
                                {#if lead.phone}
                                    <button
                                        type="button"
                                        onclick={() => (scriptModalLead = lead)}
                                        class="flex-none w-12 sm:w-14 flex justify-center items-center bg-[#3b82f6] text-white border-2 border-black rounded-lg py-2 font-bold hover:bg-[#2563eb] active:scale-95 transition-transform shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] overflow-hidden"
                                    >
                                        <Phone size={20} class="shrink-0" />
                                    </button>
                                {:else}
                                    <button
                                        disabled
                                        class="flex-none w-12 sm:w-14 flex justify-center items-center bg-gray-100 text-gray-400 border-2 border-dashed border-gray-300 rounded-lg py-2 font-bold cursor-not-allowed overflow-hidden"
                                    >
                                        <Phone size={20} class="shrink-0" />
                                    </button>
                                {/if}

                                <form
                                    method="POST"
                                    action="?/moveLead"
                                    use:enhance={({ submitter }) => {
                                        submittingId = lead.id;
                                        const statusVal =
                                            submitter?.getAttribute("value");
                                        return async ({ result, update }) => {
                                            await update({ reset: false });
                                            submittingId = null;
                                            if (
                                                result.type === "success" &&
                                                statusVal === "Interested" &&
                                                lead.idea_url
                                            ) {
                                                window.open(
                                                    lead.idea_url,
                                                    "_blank",
                                                );
                                            }
                                        };
                                    }}
                                    class="flex-1 flex gap-2 w-full"
                                >
                                    <input
                                        type="hidden"
                                        name="id"
                                        value={lead.id}
                                    />
                                    <button
                                        type="submit"
                                        name="status"
                                        value="Interested"
                                        class="flex-1 bg-[#25D366] text-white border-2 border-black rounded-lg py-2 font-black uppercase text-sm sm:text-base hover:bg-[#1da851] active:scale-95 transition-transform shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] overflow-hidden text-ellipsis whitespace-nowrap"
                                    >
                                        Interested
                                    </button>
                                    <button
                                        type="submit"
                                        name="status"
                                        value="Rejected"
                                        class="flex-1 bg-red-500 text-white border-2 border-black rounded-lg py-2 font-black uppercase text-sm sm:text-base hover:bg-red-600 active:scale-95 transition-transform shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] overflow-hidden text-ellipsis whitespace-nowrap"
                                    >
                                        Reject
                                    </button>
                                </form>
                            {/if}
                        </div>
                    </div>
                {/each}

                {#if filteredLeads.length === 0}
                    <div
                        class="p-12 text-center border-4 border-black border-dashed rounded-2xl bg-white/50 col-span-1 md:col-span-2"
                    >
                        <p class="text-xl font-bold text-gray-500">
                            No leads match this view or filter!
                        </p>
                    </div>
                {/if}
            </div>
        {/if}
    </div>

    <!-- Cold Call Script Modal -->
    {#if scriptModalLead}
        <div
            class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm overflow-y-auto"
            onclick={() => (scriptModalLead = null)}
            role="button"
            tabindex="0"
            onkeypress={(e) => e.key === "Escape" && (scriptModalLead = null)}
        >
            <div
                class="bg-white border-4 border-black rounded-3xl p-6 md:p-8 max-w-lg w-full shadow-[12px_12px_0px_0px_rgba(0,0,0,1)] relative my-auto"
                onclick={(e) => e.stopPropagation()}
                role="document"
            >
                <button
                    onclick={() => (scriptModalLead = null)}
                    class="absolute top-4 right-4 text-gray-400 hover:text-black font-black bg-gray-100 hover:bg-gray-200 rounded-full w-8 h-8 flex items-center justify-center transition-colors"
                    >✕</button
                >

                <h3
                    class="text-2xl font-black uppercase border-b-4 border-black pb-4 mb-6 tracking-tight"
                >
                    Cold Call Script
                </h3>

                <div class="space-y-6 text-lg font-bold text-gray-800">
                    <div
                        class="p-4 bg-blue-50 border-4 border-black rounded-xl shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]"
                    >
                        <p class="mb-2">
                            Hello, is this <span
                                class="bg-yellow-200 px-1 border border-black rounded uppercase text-black"
                                >{scriptModalLead.business}</span
                            >?
                        </p>
                        <p>This is Sujithra from Svantham Software.</p>
                    </div>

                    <div
                        class="p-4 bg-purple-50 border-4 border-black rounded-xl shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]"
                    >
                        <p>
                            Unga business ku <span
                                class="bg-yellow-200 px-1 border border-black rounded text-black"
                                >{scriptModalLead.remarks ||
                                    "Custom Software"}</span
                            > help thevaya? Price pathi laam nenga rombo worry pana
                            venam.
                        </p>
                    </div>

                    <div
                        class="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-8 pt-6 border-t-4 border-black border-dashed"
                    >
                        <div
                            class="p-4 bg-green-100 border-4 border-black rounded-xl shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]"
                        >
                            <h4
                                class="font-black text-green-800 flex items-center gap-2 mb-2 text-xl uppercase"
                            >
                                ✅ Yes
                            </h4>
                            <p
                                class="text-sm font-semibold text-green-900 leading-relaxed"
                            >
                                Ok sir, our technical team will contact you soon
                                for more details, thank you!
                            </p>
                        </div>
                        <div
                            class="p-4 bg-red-100 border-4 border-black rounded-xl shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]"
                        >
                            <h4
                                class="font-black text-red-800 flex items-center gap-2 mb-2 text-xl uppercase"
                            >
                                ❌ No
                            </h4>
                            <p
                                class="text-sm font-semibold text-red-900 leading-relaxed"
                            >
                                Ok sir, future la requirements vantha do contact
                                us, thank you!
                            </p>
                        </div>
                    </div>
                </div>

                <div class="mt-8 flex gap-4">
                    <button
                        onclick={() => (scriptModalLead = null)}
                        class="flex-1 bg-white border-4 border-black text-black font-black uppercase py-4 rounded-xl shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:bg-gray-100 active:scale-95 transition-transform"
                        >Close</button
                    >
                    <a
                        href="tel:{scriptModalLead.phone}"
                        class="flex-[2] bg-[#3b82f6] border-4 border-black text-white flex justify-center items-center gap-2 font-black uppercase py-4 rounded-xl shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:bg-[#2563eb] active:scale-95 transition-transform"
                    >
                        <Phone size={20} /> Dial Now
                    </a>
                </div>
            </div>
        </div>
    {/if}

    <!-- Add Lead Modal -->
    {#if showAddLeadModal}
        <div
            class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm overflow-y-auto"
            onclick={() => (showAddLeadModal = false)}
            role="button"
            tabindex="0"
            onkeypress={(e) => e.key === "Escape" && (showAddLeadModal = false)}
        >
            <div
                class="bg-white border-4 border-black rounded-3xl p-6 md:p-8 max-w-md w-full shadow-[12px_12px_0px_0px_rgba(0,0,0,1)] relative my-auto"
                onclick={(e) => e.stopPropagation()}
                role="document"
            >
                <button
                    onclick={() => (showAddLeadModal = false)}
                    class="absolute top-4 right-4 text-gray-400 hover:text-black font-black bg-gray-100 hover:bg-gray-200 rounded-full w-8 h-8 flex items-center justify-center transition-colors"
                    >✕</button
                >
                <h3
                    class="text-3xl font-black uppercase tracking-tighter mb-6 flex items-center gap-2"
                >
                    <Plus size={28} /> New Lead
                </h3>

                <form
                    method="POST"
                    action="?/addLead"
                    use:enhance={() => {
                        submittingId = -1;
                        return async ({ update, result }) => {
                            await update({ reset: true });
                            submittingId = null;
                            if (result.type === "success") {
                                showAddLeadModal = false;
                            }
                        };
                    }}
                    class="space-y-4"
                >
                    <div>
                        <label for="business" class="block font-bold mb-1"
                            >Business Name</label
                        >
                        <input
                            id="business"
                            name="business"
                            type="text"
                            required
                            class="w-full border-4 border-black rounded-xl p-3 focus:outline-none focus:ring-4 focus:ring-yellow-200 font-bold"
                            placeholder="Company / Client Name"
                        />
                    </div>
                    <div>
                        <label for="segment" class="block font-bold mb-1"
                            >Segment</label
                        >
                        <select
                            id="segment"
                            name="segment"
                            class="w-full border-4 border-black rounded-xl p-3 focus:outline-none focus:ring-4 focus:ring-yellow-200 font-bold uppercase"
                            bind:value={newLeadSegment}
                        >
                            <option value="regular">REGULAR</option>
                            <option value="billie">BILLIE</option>
                            <option value="referrer">REFERRER</option>
                            <option value="partner">PARTNER</option>
                        </select>
                    </div>
                    {#if newLeadSegment === "regular"}
                        <div>
                            <label for="remarks" class="block font-bold mb-1"
                                >Remarks</label
                            >
                            <textarea
                                id="remarks"
                                name="remarks"
                                rows="3"
                                class="w-full border-4 border-black rounded-xl p-3 focus:outline-none focus:ring-4 focus:ring-yellow-200 font-bold"
                                placeholder="Lead details..."
                            ></textarea>
                        </div>
                    {/if}
                    <div>
                        <label for="status" class="block font-bold mb-1"
                            >Status</label
                        >
                        <select
                            id="status"
                            name="status"
                            class="w-full border-4 border-black rounded-xl p-3 focus:outline-none focus:ring-4 focus:ring-yellow-200 font-bold bg-white"
                        >
                            <option value="Pending">Pending</option>
                            <option value="Contacted">Contacted</option>
                            <option value="Interested">Interested</option>
                            <option value="Converted">Converted</option>
                            <option value="Rejected">Rejected</option>
                        </select>
                    </div>
                    <button
                        type="submit"
                        disabled={submittingId === -1}
                        class="w-full bg-[#3b82f6] text-white font-black uppercase border-4 border-black rounded-xl p-4 mt-4 hover:bg-[#2563eb] active:scale-95 transition-transform shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {submittingId === -1 ? "Saving..." : "Save Lead"}
                    </button>
                </form>
            </div>
        </div>
    {/if}

    <!-- Conversion / Revenue Record Dialog -->
    {#if revenueModalLead}
        <div
            class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm overflow-y-auto"
            onclick={() => (revenueModalLead = null)}
            role="button"
            tabindex="0"
            onkeypress={(e) => e.key === "Escape" && (revenueModalLead = null)}
        >
            <div
                class="bg-white border-4 border-black rounded-3xl p-6 md:p-8 max-w-sm w-full shadow-[12px_12px_0px_0px_rgba(0,0,0,1)] relative my-auto text-center"
                onclick={(e) => e.stopPropagation()}
                role="document"
            >
                <button
                    onclick={() => (revenueModalLead = null)}
                    class="absolute top-4 right-4 text-gray-400 hover:text-black font-black bg-gray-100 hover:bg-gray-200 rounded-full w-8 h-8 flex items-center justify-center transition-colors"
                    >✕</button
                >
                <h3
                    class="text-3xl font-black uppercase tracking-tighter mb-2 text-green-600"
                >
                    Converted!
                </h3>
                <p class="font-bold mb-6 text-gray-600">
                    Enter conversion revenue for {revenueModalLead.business}
                </p>

                <form
                    method="POST"
                    action="?/updateStatus"
                    use:enhance={() => {
                        submittingId = revenueModalLead.id;
                        return async ({ update }) => {
                            await update({ reset: false });
                            submittingId = null;
                            revenueModalLead = null;
                        };
                    }}
                >
                    <input
                        type="hidden"
                        name="id"
                        value={revenueModalLead.id}
                    />
                    <input type="hidden" name="status" value="Converted" />
                    <div class="relative mb-4">
                        <span
                            class="absolute left-4 top-1/2 -translate-y-1/2 font-black text-xl text-gray-500"
                            >₹</span
                        >
                        <input
                            type="number"
                            name="revenue"
                            class="w-full text-center pl-8 text-2xl font-black border-4 border-black rounded-xl p-4 focus:outline-none focus:ring-4 focus:ring-green-200"
                            placeholder="0"
                            required
                            autofocus
                        />
                    </div>
                    <button
                        type="submit"
                        class="w-full bg-green-500 text-white font-black uppercase border-4 border-black rounded-xl p-4 hover:bg-green-600 active:scale-95 transition-transform shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]"
                    >
                        Confirm Conversion
                    </button>
                </form>
            </div>
        </div>
    {/if}

    <!-- Add Revenue Modal -->
    {#if showAddRevenueModal}
        <div
            class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm overflow-y-auto"
            onclick={() => (showAddRevenueModal = false)}
            role="button"
            tabindex="0"
            onkeypress={(e) =>
                e.key === "Escape" && (showAddRevenueModal = false)}
        >
            <div
                class="bg-white border-4 border-black rounded-3xl p-6 md:p-8 max-w-md w-full shadow-[12px_12px_0px_0px_rgba(0,0,0,1)] relative my-auto"
                onclick={(e) => e.stopPropagation()}
                role="document"
            >
                <button
                    onclick={() => (showAddRevenueModal = false)}
                    class="absolute top-4 right-4 text-gray-400 hover:text-black font-black bg-gray-100 hover:bg-gray-200 rounded-full w-8 h-8 flex items-center justify-center transition-colors"
                    >✕</button
                >
                <h3
                    class="text-3xl font-black uppercase tracking-tighter mb-6 flex items-center gap-2 text-green-700"
                >
                    <Plus size={28} /> Log Revenue
                </h3>

                <form
                    method="POST"
                    action="?/addRevenueRecord"
                    use:enhance={() => {
                        submittingId = -1;
                        return async ({ update, result }) => {
                            await update({ reset: true });
                            submittingId = null;
                            if (result.type === "success") {
                                showAddRevenueModal = false;
                            }
                        };
                    }}
                    class="space-y-4"
                >
                    <div>
                        <label for="business_rev" class="block font-bold mb-1"
                            >Business / Partner Name</label
                        >
                        <input
                            id="business_rev"
                            name="business"
                            type="text"
                            required
                            class="w-full border-4 border-black rounded-xl p-3 focus:outline-none focus:ring-4 focus:ring-yellow-200 font-bold"
                            placeholder="Client or Partner Name"
                        />
                    </div>

                    <div>
                        <label for="rev_type" class="block font-bold mb-1"
                            >Revenue Type</label
                        >
                        <select
                            id="rev_type"
                            name="type"
                            class="w-full border-4 border-black rounded-xl p-3 focus:outline-none focus:ring-4 focus:ring-yellow-200 font-bold bg-white"
                        >
                            <option value="recurring_partner"
                                >Agency Recurring Retainer (Monthly)</option
                            >
                            <option value="referral_fee"
                                >CA Referral Commission (Payout / Earned)</option
                            >
                            <option value="one_time"
                                >One-Time Project Build</option
                            >
                        </select>
                    </div>

                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label for="amount" class="block font-bold mb-1"
                                >Amount (₹)</label
                            >
                            <input
                                id="amount"
                                name="amount"
                                type="number"
                                required
                                class="w-full border-4 border-black rounded-xl p-3 focus:outline-none focus:ring-4 focus:ring-yellow-200 font-bold"
                                placeholder="50000"
                            />
                        </div>
                        <div>
                            <label for="period" class="block font-bold mb-1"
                                >Billing Period</label
                            >
                            <input
                                id="period"
                                name="period"
                                type="month"
                                required
                                value={currentMonth}
                                class="w-full border-4 border-black rounded-xl p-3 focus:outline-none focus:ring-4 focus:ring-yellow-200 font-bold bg-white"
                            />
                        </div>
                    </div>

                    <div>
                        <label for="notes" class="block font-bold mb-1"
                            >Notes / Description</label
                        >
                        <textarea
                            id="notes"
                            name="notes"
                            rows="2"
                            class="w-full border-4 border-black rounded-xl p-3 focus:outline-none focus:ring-4 focus:ring-yellow-200 font-bold"
                            placeholder="e.g. September white-label backend retainer for 2 client webapps"
                        ></textarea>
                    </div>

                    <button
                        type="submit"
                        disabled={submittingId === -1}
                        class="w-full bg-green-500 text-white font-black uppercase border-4 border-black rounded-xl p-4 mt-4 hover:bg-green-600 active:scale-95 transition-transform shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {submittingId === -1
                            ? "Logging..."
                            : "Log Revenue Record"}
                    </button>
                </form>
            </div>
        </div>
    {/if}
{/if}
