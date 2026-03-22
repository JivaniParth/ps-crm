import { useState } from 'react';
import PropTypes from 'prop-types';
import {
    BarChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
    ComposedChart, RadialBarChart, RadialBar, PolarAngleAxis
} from 'recharts';

export default function AnalyticsCommandCenter({ analytics, onDrillDown }) {
    const { ward_unresolved, department_performance, satisfaction_score, anomalies, live_feed } = analytics;

    // Custom Tooltips for glassmorphism
    const CustomTooltip = ({ active, payload, label }) => {
        if (active && payload && payload.length) {
            return (
                <div style={{ background: 'var(--surface)', padding: '1rem', border: '1px solid var(--accent)', borderRadius: '12px', boxShadow: '0 8px 32px rgba(0,0,0,0.5)' }}>
                    <p style={{ margin: 0, fontWeight: 'bold' }}>{label}</p>
                    {payload.map(p => (
                        <p key={p.dataKey} style={{ margin: '0.2rem 0', color: p.color }}>
                            {p.name}: {p.value}
                        </p>
                    ))}
                    <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>Click to view details</p>
                </div>
            );
        }
        return null;
    };

    return (
        <div className="command-center">
            {/* Anomaly Detection Banner */}
            {anomalies && anomalies.length > 0 && (
                <div className="anomaly-banner" style={{ background: 'linear-gradient(45deg, #ef4444, #b91c1c)', color: 'white', padding: '1rem', borderRadius: '12px', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '1rem', animation: 'pulse 2s infinite' }}>
                    <span style={{ fontSize: '1.5rem' }}>⚠️</span>
                    <div>
                        <h4 style={{ margin: 0 }}>System Anomaly Detected</h4>
                        <p style={{ margin: '0.2rem 0 0 0', fontSize: '0.9rem' }}>{anomalies[0].message}</p>
                    </div>
                </div>
            )}

            <div className="charts-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '1.5rem' }}>

                {/* Ward Unresolved Hotspots (Heatmap Proxy) */}
                <article className="card" style={{ display: 'flex', flexDirection: 'column' }}>
                    <h4>Ward Hotspots (Unresolved)</h4>
                    <p className="helper-text" style={{ marginBottom: '1rem' }}>Click a bar to view tickets.</p>
                    <div style={{ width: '100%', height: 300 }}>
                        <ResponsiveContainer>
                            <BarChart data={ward_unresolved} margin={{ top: 10, right: 10, left: -20, bottom: 0 }} onClick={(e) => {
                                if (e && e.activePayload) onDrillDown({ ward: e.activePayload[0].payload.ward, status: 'Open' });
                            }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                                <XAxis dataKey="ward" stroke="var(--text-muted)" fontSize={12} />
                                <YAxis stroke="var(--text-muted)" fontSize={12} />
                                <Tooltip content={<CustomTooltip />} cursor={{ fill: 'color-mix(in srgb, var(--accent) 20%, transparent)' }} />
                                <Legend />
                                <Bar dataKey="open" name="Open" stackId="a" fill="var(--accent)" radius={[0, 0, 4, 4]} />
                                <Bar dataKey="escalated" name="Escalated" stackId="a" fill="#ef4444" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </article>

                {/* Department Performance Index */}
                <article className="card" style={{ display: 'flex', flexDirection: 'column' }}>
                    <h4>Department Performance Index</h4>
                    <p className="helper-text" style={{ marginBottom: '1rem' }}>Avg Resolution Time vs SLA Threshold.</p>
                    <div style={{ width: '100%', height: 300 }}>
                        <ResponsiveContainer>
                            <ComposedChart data={department_performance} margin={{ top: 10, right: 10, left: -20, bottom: 0 }} onClick={(e) => {
                                if (e && e.activePayload) onDrillDown({ department: e.activePayload[0].payload.name });
                            }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                                <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={12} />
                                <YAxis stroke="var(--text-muted)" fontSize={12} />
                                <Tooltip content={<CustomTooltip />} cursor={{ fill: 'color-mix(in srgb, var(--accent) 20%, transparent)' }} />
                                <Legend />
                                <Bar dataKey="avg_time_hours" name="Avg Time (Hrs)" barSize={20} fill="var(--blue)" radius={[4, 4, 0, 0]} />
                                <Line type="monotone" dataKey="sla_hours" name="SLA Target" stroke="#ef4444" strokeWidth={3} dot={{ r: 4 }} />
                            </ComposedChart>
                        </ResponsiveContainer>
                    </div>
                </article>

                {/* Public Satisfaction Score */}
                <article className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <h4 style={{ alignSelf: 'flex-start' }}>Public CSAT Score</h4>
                    <p className="helper-text" style={{ alignSelf: 'flex-start', marginBottom: '1rem' }}>Derived from SLA compliance.</p>
                    <div style={{ width: '100%', height: 250, display: 'flex', justifyContent: 'center' }}>
                        <ResponsiveContainer width={250} height={250}>
                            <RadialBarChart cx="50%" cy="50%" innerRadius="70%" outerRadius="100%" barSize={20} data={[{ name: 'Score', value: satisfaction_score, fill: satisfaction_score > 80 ? 'var(--green)' : 'var(--accent)' }]} startAngle={180} endAngle={0}>
                                <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
                                <RadialBar minAngle={15} background={{ fill: '#333' }} clockWise dataKey="value" cornerRadius={10} />
                                <text x="50%" y="45%" textAnchor="middle" dominantBaseline="middle" className="progress-label" style={{ fill: 'var(--text)', fontSize: '2.5rem', fontWeight: 'bold' }}>
                                    {satisfaction_score}%
                                </text>
                                <text x="50%" y="60%" textAnchor="middle" dominantBaseline="middle" style={{ fill: 'var(--text-muted)', fontSize: '0.9rem' }}>
                                    Satisfaction
                                </text>
                            </RadialBarChart>
                        </ResponsiveContainer>
                    </div>
                </article>

                {/* Live Resolution Feed */}
                <article className="card" style={{ display: 'flex', flexDirection: 'column' }}>
                    <h4>Live Resolution Feed</h4>
                    <p className="helper-text" style={{ marginBottom: '1rem' }}>Real-time field updates.</p>
                    <div className="live-feed-container" style={{ flexGrow: 1, overflowY: 'auto', maxHeight: '250px', paddingRight: '0.5rem' }}>
                        {(!live_feed || live_feed.length === 0) && <p className="helper-text">No recent resolutions.</p>}
                        {live_feed && live_feed.map((feed, idx) => (
                            <div key={idx} style={{ padding: '0.8rem', borderLeft: '4px solid var(--green)', background: 'color-mix(in srgb, var(--green) 10%, transparent)', marginBottom: '0.5rem', borderRadius: '0 8px 8px 0' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <strong>{feed.ticket_id}</strong>
                                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{new Date(feed.resolved_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                                </div>
                                <p style={{ margin: '0.3rem 0 0 0', fontSize: '0.85rem' }}>{feed.department} issue resolved in {feed.ward}.</p>
                            </div>
                        ))}
                    </div>
                </article>
            </div>
        </div>
    );
}

AnalyticsCommandCenter.propTypes = {
    analytics: PropTypes.object.isRequired,
    onDrillDown: PropTypes.func.isRequired
};
