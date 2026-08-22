/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class MonetaDashboard extends Component {
    static template = "moneta_finance.MonetaDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.netWorthCanvas = useRef("netWorthCanvas");
        this.donutCanvas = useRef("donutCanvas");

        this.state = useState({
            loading: true,
            data: {
                currency_symbol: "$",
                currency_name: "USD",
                net_worth: 0,
                net_worth_formatted: "$0.00",
                total_assets_formatted: "$0.00",
                total_liabilities_formatted: "$0.00",
                recent_transactions: [],
                investment_holdings: [],
                asset_allocation: [],
                net_worth_history: [],
                sankey_data: {
                    income: 0,
                    expenses: 0,
                    savings: 0,
                    flows: [],
                },
                monte_carlo_cone: {
                    p10_formatted: "$0",
                    p50_formatted: "$0",
                    p90_formatted: "$0",
                    success_rate: 0,
                },
                emergency_runway_months: 0,
                fire_progress_pct: 0,
            },
            timeframe: "1Y",
        });

        this.charts = {
            netWorth: null,
            donut: null,
        };

        onWillStart(async () => {
            await this.loadData();
        });

        onMounted(() => {
            this.renderCharts();
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            const result = await this.orm.call(
                "moneta.dashboard",
                "get_dashboard_payload",
                []
            );
            if (result && typeof result === "object") {
                this.state.data = {
                    ...this.state.data,
                    ...result,
                    recent_transactions: result.recent_transactions || [],
                    investment_holdings: result.investment_holdings || [],
                    asset_allocation: result.asset_allocation || [],
                    net_worth_history: result.net_worth_history || [],
                    sankey_data: result.sankey_data || { income: 0, expenses: 0, savings: 0, flows: [] },
                    monte_carlo_cone: result.monte_carlo_cone || { p10_formatted: "$0", p50_formatted: "$0", p90_formatted: "$0" },
                };
            }
        } catch (err) {
            console.error("Failed to load Moneta dashboard data:", err);
        } finally {
            this.state.loading = false;
        }
    }

    async onRefreshData() {
        await this.loadData();
        this.renderCharts();
    }

    setTimeframe(tf) {
        this.state.timeframe = tf;
        this.renderNetWorthChart();
    }

    renderCharts() {
        if (typeof Chart === "undefined") {
            return;
        }
        setTimeout(() => {
            this.renderNetWorthChart();
            this.renderDonutChart();
        }, 60);
    }

    renderNetWorthChart() {
        if (!this.netWorthCanvas.el) return;
        const ctx = this.netWorthCanvas.el.getContext("2d");
        if (this.charts.netWorth) {
            this.charts.netWorth.destroy();
        }

        const history = this.state.data.net_worth_history || [];
        const labels = history.map((h) => h.date);
        const dataPoints = history.map((h) => h.amount);

        const gradient = ctx.createLinearGradient(0, 0, 0, 140);
        gradient.addColorStop(0, "rgba(56, 189, 248, 0.45)");
        gradient.addColorStop(1, "rgba(56, 189, 248, 0.0)");

        this.charts.netWorth = new Chart(ctx, {
            type: "line",
            data: {
                labels: labels.length ? labels : ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
                datasets: [
                    {
                        label: "Net Worth",
                        data: dataPoints.length ? dataPoints : [0, 0, 0, 0, 0, 0],
                        borderColor: "#38bdf8",
                        borderWidth: 2.5,
                        pointBackgroundColor: "#0284c7",
                        pointBorderColor: "#38bdf8",
                        pointRadius: 3,
                        pointHoverRadius: 5,
                        backgroundColor: gradient,
                        fill: true,
                        tension: 0.35,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: "#0f172a",
                        titleColor: "#94a3b8",
                        bodyColor: "#38bdf8",
                        borderColor: "rgba(255,255,255,0.1)",
                        borderWidth: 1,
                        callbacks: {
                            label: (context) => {
                                return ` Net Worth: ${this.state.data.currency_symbol || "$"}${context.parsed.y.toLocaleString()}`;
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: "#64748b", font: { size: 10 } },
                    },
                    y: {
                        display: false,
                        grid: { display: false },
                    },
                },
            },
        });
    }

    renderDonutChart() {
        if (!this.donutCanvas.el) return;
        const ctx = this.donutCanvas.el.getContext("2d");
        if (this.charts.donut) {
            this.charts.donut.destroy();
        }

        const allocation = this.state.data.asset_allocation || [
            { label: "Tech", value: 48, color: "#3b82f6" },
            { label: "ETF", value: 34, color: "#06b6d4" },
            { label: "Cash", value: 18, color: "#10b981" },
        ];

        this.charts.donut = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: allocation.map((a) => a.label),
                datasets: [
                    {
                        data: allocation.map((a) => a.value),
                        backgroundColor: allocation.map((a) => a.color),
                        borderWidth: 2,
                        borderColor: "#0f172a",
                        hoverOffset: 4,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "70%",
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: "#0f172a",
                        bodyColor: "#ffffff",
                        borderColor: "rgba(255,255,255,0.1)",
                        borderWidth: 1,
                    },
                },
            },
        });
    }

    async toggleCleared(txId) {
        try {
            await this.orm.call("moneta.transaction", "action_toggle_cleared", [[txId]]);
            const tx = this.state.data.recent_transactions.find((t) => t.id === txId);
            if (tx) {
                if (tx.cleared_status === "U") tx.cleared_status = "C";
                else if (tx.cleared_status === "C") tx.cleared_status = "R";
                else tx.cleared_status = "U";
            }
        } catch (err) {
            console.error("Failed to toggle transaction cleared status:", err);
        }
    }

    onOpenTransactions() {
        this.action.doAction("moneta_finance.action_moneta_transaction");
    }

    onOpenHoldings() {
        this.action.doAction("moneta_finance.action_moneta_holding");
    }

    onOpenInsights() {
        this.action.doAction("moneta_finance.action_moneta_insight");
    }

    onOpenMonteCarlo() {
        this.action.doAction("moneta_finance.action_moneta_monte_carlo");
    }
}

registry.category("actions").add("moneta_finance.dashboard_client_action", MonetaDashboard);
