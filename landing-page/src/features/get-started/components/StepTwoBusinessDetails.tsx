import { inputClasses, selectClasses } from "../constants";
import type { FormData } from "../types";

type Props = {
  formData: {
    business_name: string;
    business_category: string;
    city: string;
    employees_range: string;
    monthly_revenue: string;
    business_age: string;
  };
  onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => void;
};

export function StepTwoBusinessDetails({ formData, onChange }: Props) {
  return (
    <div className="p-6 md:p-10 md:rounded-3xl rounded-2xl border border-white/10 bg-white/[0.02] shadow-xl flex flex-col gap-6">
      <h2 className="text-2xl font-medium text-white/90 border-b border-white/5 pb-4">
        Step 2 — Business Details
      </h2>
      <div className="flex flex-col gap-3">
        <label className="text-sm font-medium text-white/80">
          Company / Business Name <span className="text-red-400">*</span>
        </label>
        <input
          required
          type="text"
          name="business_name"
          className={inputClasses}
          placeholder="Your Business Name"
          value={formData.business_name}
          onChange={onChange}
        />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="flex flex-col gap-3">
          <label className="text-sm font-medium text-white/80">Business Category</label>
          <select
            name="business_category"
            className={selectClasses}
            value={formData.business_category}
            onChange={onChange}
          >
            <option value="" disabled>Select a category</option>
            <option>Retail/Shop</option>
            <option>Restaurant/Food</option>
            <option>Manufacturing</option>
            <option>Wholesale/Distribution</option>
            <option>Services</option>
            <option>E-commerce/Online</option>
            <option>Education/Coaching</option>
            <option>Real Estate</option>
            <option>Logistics/Transport</option>
            <option>Freelance/Consulting</option>
            <option>Other</option>
          </select>
        </div>
        <div className="flex flex-col gap-3">
          <label className="text-sm font-medium text-white/80">
            City / Location <span className="text-red-400">*</span>
          </label>
          <input
            required
            type="text"
            name="city"
            className={inputClasses}
            placeholder="City, Country"
            value={formData.city}
            onChange={onChange}
          />
        </div>
        <div className="flex flex-col gap-3">
          <label className="text-sm font-medium text-white/80">Number of Employees</label>
          <select
            name="employees_range"
            className={selectClasses}
            value={formData.employees_range}
            onChange={onChange}
          >
            <option value="" disabled>Select employees</option>
            <option>Just me</option>
            <option>2–5</option>
            <option>6–15</option>
            <option>16–50</option>
            <option>51–100</option>
            <option>100+</option>
          </select>
        </div>
        <div className="flex flex-col gap-3">
          <label className="text-sm font-medium text-white/80">Monthly Revenue</label>
          <select
            name="monthly_revenue"
            className={selectClasses}
            value={formData.monthly_revenue}
            onChange={onChange}
          >
            <option value="" disabled>Select monthly revenue</option>
            <option>Under ₹50K</option>
            <option>₹50K–₹2L</option>
            <option>₹2L–₹10L</option>
            <option>₹10L–₹50L</option>
            <option>Above ₹50L</option>
          </select>
        </div>
      </div>
      <div className="flex flex-col gap-3">
        <label className="text-sm font-medium text-white/80">Business Age</label>
        <select
          name="business_age"
          className={selectClasses}
          value={formData.business_age}
          onChange={onChange}
        >
          <option value="" disabled>Select business age</option>
          <option>0–6 months</option>
          <option>Less than 1 year</option>
          <option>1–3 years</option>
          <option>3–7 years</option>
          <option>7+ years</option>
        </select>
      </div>
    </div>
  );
}