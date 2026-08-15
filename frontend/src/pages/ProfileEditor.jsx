import React, { useState, useEffect } from 'react';
import { fetchProfile, updateProfile } from '../api/client';
import { UserCheck, Save, CheckCircle } from 'lucide-react';

export default function ProfileEditor() {
  const [formData, setFormData] = useState({
    fleet_size: 120,
    annual_turnover: 150000000,
    years_experience: 7,
    past_contract_sizes: '75000000, 90000000',
    preferred_geographies: 'Rajasthan, Haryana, Delhi, Gujarat'
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    const loadProfile = async () => {
      try {
        setLoading(true);
        const p = await fetchProfile();
        setFormData({
          fleet_size: p.fleet_size,
          annual_turnover: p.annual_turnover,
          years_experience: p.years_experience,
          past_contract_sizes: (p.past_contract_sizes || []).join(', '),
          preferred_geographies: (p.preferred_geographies || []).join(', ')
        });
      } catch (err) {
        console.error("Failed to load profile:", err);
      } finally {
        setLoading(false);
      }
    };
    loadProfile();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setSaving(true);
      setSavedSuccess(false);

      const pastContracts = formData.past_contract_sizes
        .split(',')
        .map(v => parseFloat(v.trim()))
        .filter(v => !isNaN(v));

      const geographies = formData.preferred_geographies
        .split(',')
        .map(g => g.trim())
        .filter(g => g.length > 0);

      const payload = {
        fleet_size: parseInt(formData.fleet_size, 10),
        annual_turnover: parseFloat(formData.annual_turnover),
        years_experience: parseInt(formData.years_experience, 10),
        past_contract_sizes: pastContracts,
        preferred_geographies: geographies
      };

      await updateProfile(payload);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err) {
      alert("Failed to update profile: " + err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="text-center py-20">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
        <p className="text-sm text-slate-400">Loading company profile...</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      
      <div className="glass-card p-6 rounded-2xl border border-slate-800 space-y-2">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
            <UserCheck className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white font-heading">Company Operational Profile</h1>
            <p className="text-xs text-slate-400">Deterministic screening rules evaluate tenders against these exact metrics.</p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="glass-card p-6 rounded-2xl border border-slate-800 space-y-5">
        
        {savedSuccess && (
          <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-xs flex items-center gap-2">
            <CheckCircle className="w-4 h-4" />
            <span>Profile successfully updated! All tender screening checks will re-evaluate against new profile.</span>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Active Fleet Size (Buses)</label>
            <input
              type="number"
              value={formData.fleet_size}
              onChange={(e) => setFormData({ ...formData, fleet_size: e.target.value })}
              className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 font-mono"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Annual Turnover (INR)</label>
            <input
              type="number"
              value={formData.annual_turnover}
              onChange={(e) => setFormData({ ...formData, annual_turnover: e.target.value })}
              className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 font-mono"
              required
            />
            <p className="text-[10px] text-slate-500 mt-1">₹{(formData.annual_turnover / 1e7).toFixed(2)} Crore</p>
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">Years of Operating Experience</label>
          <input
            type="number"
            value={formData.years_experience}
            onChange={(e) => setFormData({ ...formData, years_experience: e.target.value })}
            className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 font-mono"
            required
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">Executed Past Contract Values (INR, comma-separated)</label>
          <input
            type="text"
            value={formData.past_contract_sizes}
            onChange={(e) => setFormData({ ...formData, past_contract_sizes: e.target.value })}
            className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 font-mono"
            placeholder="75000000, 90000000"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">Preferred Operating Geographies (comma-separated)</label>
          <input
            type="text"
            value={formData.preferred_geographies}
            onChange={(e) => setFormData({ ...formData, preferred_geographies: e.target.value })}
            className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 font-mono"
            placeholder="Rajasthan, Haryana, Delhi"
          />
        </div>

        <button
          type="submit"
          disabled={saving}
          className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50"
        >
          <Save className="w-4 h-4" />
          <span>{saving ? 'Saving Profile...' : 'Save Profile & Update Screening Rules'}</span>
        </button>

      </form>

    </div>
  );
}
