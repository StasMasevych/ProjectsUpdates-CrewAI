"use client";

import React from "react";
import { useState } from "react";

// Type definitions
interface Project {
  name: string;
  location: string;
  capacity: string;
  timeline: string;
  investment: string;
  developer: string;
  source_url: string;
  source_name: string;
  status: string;
  category: string;
  date: string;
  keyPoints: string[];
  partners: string[];
}

// Simplified interface with only required fields
interface AnalysisSummary {
  countries_analyzed: string[];
  major_developers: string[];
  most_promising_projects: string[];
}

interface AccumulatedAnalysis {
  timestamp: string;
  summary: AnalysisSummary;
  projects_by_country: {
    [country: string]: Project[];
  };
}

interface SearchResult {
  url: string;
  description: string;
  country: string;
}

interface ApiResponse {
  search_results: SearchResult[];
  analysis: AccumulatedAnalysis;
  error?: string;
}

type ProgressUpdate = {
  country: string;
  step: string;
};

const REGIONS = [
  { id: "USA", name: "United States", flag: "🇺🇸" },
  { id: "EU", name: "Europe", flag: "🇪🇺" },
];

const TECHNOLOGIES = [
  { id: "solar", name: "Solar", icon: "☀️" },
  { id: "wind", name: "Wind", icon: "🌪️" },
  { id: "bess", name: "BESS", icon: "🔋" },
  { id: "biogas", name: "Biogas", icon: "♻️" },
  { id: "h2", name: "H2", icon: "💧" },
];

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function Home() {
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState<ProgressUpdate | null>(null);
  const [result, setResult] = useState<ApiResponse | null>(null);
  const [selectedRegion, setSelectedRegion] = useState<string>("");
  const [selectedTechnology, setSelectedTechnology] = useState<string>("");
  const [error, setError] = useState<string>("");

  const getStepEmoji = (step: string): string => {
    switch (step) {
      case "starting":
        return "🚀";
      case "searching":
        return "🔍";
      case "processing":
        return "⚙️";
      case "analyzing":
        return "📊";
      case "combining":
        return "🔄";
      case "complete":
        return "✅";
      case "error":
        return "❌";
      default:
        return "📝";
    }
  };

  const fetchProjects = async (): Promise<void> => {
    if (!selectedRegion || !selectedTechnology) {
      setError("Please select both region and technology");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    // Set up event source for progress updates
    const eventSource = new EventSource(`/api/progress`);

    eventSource.onmessage = (event: MessageEvent) => {
      const data = JSON.parse(event.data) as ProgressUpdate;
      setProgress(data);

      if (data.step === "complete" || data.step === "error") {
        eventSource.close();
      }
    };

    try {
      console.log(
        "Fetching from:",
        `${API_BASE_URL}/api/projects?region=${selectedRegion}&technology=${selectedTechnology}`
      );

      const response = await fetch(
        `${API_BASE_URL}/api/projects?region=${selectedRegion}&technology=${selectedTechnology}`,
        {
          method: "GET",
          headers: {
            Accept: "application/json",
          },
        }
      );

      console.log("Response status:", response.status);
      const responseText = await response.text();
      console.log("Response text:", responseText);

      if (!response.ok) {
        throw new Error(
          `HTTP error! status: ${response.status}, body: ${responseText}`
        );
      }

      const data: ApiResponse = JSON.parse(responseText);
      if (data.error) {
        setError(data.error);
      } else {
        setResult(data);
      }
    } catch (err) {
      console.error("Detailed fetch error:", err);
      setError(err instanceof Error ? err.message : "Failed to fetch projects");
    } finally {
      setLoading(false);
      setProgress(null);
      eventSource.close();
    }
  };

  return (
    <main className="min-h-screen p-8 bg-gray-50">
      <h1 className="text-4xl font-bold mb-8">Energy Projects Analyzer 🌍</h1>

      {/* Controls */}
      <div className="mb-8 flex gap-4 items-center">
        <select
          className="p-2 border rounded-lg"
          value={selectedRegion}
          onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
            setSelectedRegion(e.target.value)
          }
        >
          <option value="">Select Region</option>
          {REGIONS.map((region) => (
            <option key={region.id} value={region.id}>
              {region.flag} {region.name}
            </option>
          ))}
        </select>

        <select
          className="p-2 border rounded-lg"
          value={selectedTechnology}
          onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
            setSelectedTechnology(e.target.value)
          }
        >
          <option value="">Select Technology</option>
          {TECHNOLOGIES.map((tech) => (
            <option key={tech.id} value={tech.id}>
              {tech.icon} {tech.name}
            </option>
          ))}
        </select>

        <button
          onClick={fetchProjects}
          disabled={loading}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-400"
        >
          {loading ? "Processing..." : "Analyze Projects"}
        </button>
      </div>

      {/* Progress Display */}
      {loading && progress && (
        <div className="mb-8 p-4 bg-white rounded-lg shadow">
          <h3 className="text-xl font-semibold mb-4">Analysis Progress</h3>
          <div className="flex items-center gap-2">
            {getStepEmoji(progress.step)}
            <span className="font-medium">
              {progress.country === "all"
                ? "Finalizing Analysis"
                : `Analyzing ${progress.country}`}
            </span>
            <span className="text-gray-600">
              - {progress.step.charAt(0).toUpperCase() + progress.step.slice(1)}
            </span>
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="mb-8 p-4 bg-red-50 text-red-600 rounded-lg">
          ❌ {error}
        </div>
      )}

      {/* Results Display */}
      {result && !loading && (
        <div className="space-y-8">
          <section className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-2xl font-semibold mb-4">Analysis Results</h2>

            {/* Overall Summary - Simplified */}
            <div className="mb-8">
              <h3 className="text-xl font-semibold mb-4">Overall Summary</h3>
              <div className="p-4 bg-gray-50 rounded-lg">
                <div>
                  <p className="font-medium">Countries Analyzed:</p>
                  <p className="text-xl">
                    {result.analysis.summary.countries_analyzed.length > 0
                      ? result.analysis.summary.countries_analyzed.join(", ")
                      : "No countries analyzed"}
                  </p>
                </div>
              </div>

              {/* Most Promising Projects */}
              {result.analysis.summary.most_promising_projects &&
                result.analysis.summary.most_promising_projects.length > 0 && (
                  <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                    <h4 className="font-medium mb-2">
                      Most Promising Projects:
                    </h4>
                    <ul className="list-disc pl-5 space-y-2">
                      {result.analysis.summary.most_promising_projects.map(
                        (project, index) => (
                          <li key={index} className="text-gray-800">
                            {project}
                          </li>
                        )
                      )}
                    </ul>
                  </div>
                )}
            </div>

            {/* Projects by Country */}
            <div className="space-y-6">
              <h3 className="text-xl font-semibold">Projects by Country</h3>
              {Object.entries(result.analysis.projects_by_country).map(
                ([country, projects]) => (
                  <div key={country} className="border-t pt-4">
                    <h4 className="text-lg font-medium mb-3">
                      {country} ({projects.length} projects)
                    </h4>
                    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                      {projects.map((project, index) => (
                        <div
                          key={index}
                          className="bg-white rounded-xl shadow-lg hover:shadow-xl transition-shadow duration-300 overflow-hidden"
                        >
                          {/* Project Header */}
                          <div className="p-4 border-b bg-gradient-to-r from-blue-50 to-blue-100">
                            <h5 className="text-lg font-semibold text-gray-900 mb-1">
                              {project.name}
                            </h5>
                            <div className="flex items-center text-sm text-gray-600">
                              <span className="mr-2">📍</span>
                              {project.location}
                            </div>
                          </div>

                          {/* Project Details */}
                          <div className="p-4 space-y-3">
                            <div className="grid grid-cols-2 gap-3 text-sm">
                              <div className="flex items-center">
                                <span className="text-lg mr-2">⚡</span>
                                <div>
                                  <p className="text-gray-600">Capacity</p>
                                  <p className="font-medium">
                                    {project.capacity}
                                  </p>
                                </div>
                              </div>
                              <div className="flex items-center">
                                <span className="text-lg mr-2">💰</span>
                                <div>
                                  <p className="text-gray-600">Investment</p>
                                  <p className="font-medium">
                                    {project.investment}
                                  </p>
                                </div>
                              </div>
                              <div className="flex items-center">
                                <span className="text-lg mr-2">👥</span>
                                <div>
                                  <p className="text-gray-600">Developer</p>
                                  <p className="font-medium">
                                    {project.developer}
                                  </p>
                                </div>
                              </div>
                              <div className="flex items-center">
                                <span className="text-lg mr-2">📅</span>
                                <div>
                                  <p className="text-gray-600">Timeline</p>
                                  <p className="font-medium">
                                    {project.timeline}
                                  </p>
                                </div>
                              </div>
                            </div>

                            {/* Key Points */}
                            <div className="mt-3 pt-3 border-t border-gray-100">
                              <h6 className="font-medium text-sm mb-2">
                                Key Points:
                              </h6>
                              <ul className="list-disc pl-5 text-sm space-y-1">
                                {project.keyPoints &&
                                project.keyPoints.length > 0 ? (
                                  project.keyPoints.map((point, idx) => (
                                    <li key={idx}>{point}</li>
                                  ))
                                ) : (
                                  <li>No key points available</li>
                                )}
                              </ul>
                            </div>

                            {/* Status Badge */}
                            <div className="pt-2 flex flex-wrap gap-2">
                              <span
                                className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                                bg-blue-100 text-blue-800"
                              >
                                Status: {project.status}
                              </span>
                              <span
                                className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                                bg-green-100 text-green-800"
                              >
                                Category: {project.category}
                              </span>
                              <span
                                className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                                bg-yellow-100 text-yellow-800"
                              >
                                Date: {project.date}
                              </span>
                            </div>

                            {/* Source Information */}
                            <div className="mt-4 pt-3 border-t border-gray-100">
                              <div className="text-sm text-gray-600">
                                <p className="flex items-center mb-1">
                                  <span className="text-lg mr-2">📰</span>
                                  Source: {project.source_name}
                                </p>
                                {project.source_url && (
                                  <a
                                    href={project.source_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-blue-600 hover:text-blue-800 hover:underline flex items-center"
                                  >
                                    <span className="text-lg mr-2">🔗</span>
                                    Read More
                                  </a>
                                )}
                              </div>
                            </div>

                            {/* Partners */}
                            {project.partners &&
                              project.partners.length > 0 && (
                                <div className="mt-3 pt-3 border-t border-gray-100">
                                  <h6 className="font-medium text-sm mb-2">
                                    Partners:
                                  </h6>
                                  <div className="flex flex-wrap gap-2">
                                    {project.partners.map((partner, idx) => (
                                      <span
                                        key={idx}
                                        className="px-2 py-1 bg-purple-100 text-purple-800 rounded-full text-xs"
                                      >
                                        {partner}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )
              )}
            </div>

            {/* Search Results Summary */}
            <div className="mt-8 pt-6 border-t">
              <h3 className="text-xl font-semibold mb-4">
                Search Results by Country
              </h3>
              {Object.entries(
                result.search_results.reduce(
                  (acc: Record<string, SearchResult[]>, curr) => {
                    if (!acc[curr.country]) {
                      acc[curr.country] = [];
                    }
                    acc[curr.country].push(curr);
                    return acc;
                  },
                  {}
                )
              ).map(([country, results]) => (
                <div key={country} className="mb-4">
                  <h4 className="font-medium mb-2">{country}</h4>
                  <ul className="list-disc pl-5 space-y-2">
                    {results.map((result: SearchResult, index: number) => (
                      <li key={index}>
                        <a
                          href={result.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline"
                        >
                          {result.description}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
