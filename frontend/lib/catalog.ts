/** The 19 schemes the rule engine can name. Display only — the call decides eligibility. */

export const SCHEMES: { name: string; who: string }[] = [
  { name: "PM-KISAN", who: "Farmers" },
  { name: "PM Fasal Bima", who: "Crop loss" },
  { name: "Ayushman Bharat", who: "Hospital cover" },
  { name: "Ayushman Vay Vandana", who: "Age 70+" },
  { name: "PM Vishwakarma", who: "Artisans" },
  { name: "PMAY-Gramin", who: "Rural housing" },
  { name: "PM Ujjwala", who: "Cooking gas" },
  { name: "MGNREGA", who: "Village work" },
  { name: "Old-age pension", who: "NSAP" },
  { name: "Widow pension", who: "NSAP" },
  { name: "Disability pension", who: "NSAP" },
  { name: "PM Matru Vandana", who: "Mothers" },
  { name: "PM SVANidhi", who: "Street vendors" },
  { name: "e-Shram", who: "Unorganised work" },
  { name: "PM Jan Dhan", who: "Bank account" },
  { name: "Gruha Lakshmi", who: "Karnataka" },
  { name: "Ladki Bahin", who: "Maharashtra" },
  { name: "Rythu Bharosa", who: "Telangana" },
  { name: "Lakshmir Bhandar", who: "West Bengal" },
];

export const STEPS = [
  {
    n: "01",
    title: "Speak",
    body: "Talk the way you would at a CSC counter. Hindi, Kannada, Telugu, Tamil, Marathi, or Hinglish.",
  },
  {
    n: "02",
    title: "Match",
    body: "JanVaani fills the form and checks 19 schemes with a fixed rule. The voice never decides eligibility.",
  },
  {
    n: "03",
    title: "Slip",
    body: "Leave with a Ready Slip PDF, a QR code, the papers to carry, and what to fix before the counter.",
  },
] as const;
