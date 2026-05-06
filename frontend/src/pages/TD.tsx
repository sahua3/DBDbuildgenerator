import React from 'react';

export default function TD() {
    return (
        <div className="min-h-screen py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-3xl mx-auto">
                <h1 className="text-4xl font-bold text-white-900 mb-8">To Dos and Known Issues</h1>
                
                <div className="space-y-6">
                        <h2 className="text-xl font-semibold text-red-800 mb-2">Issue: System Evaluation</h2>
                        <p className="text-white-600">
                            Currently, the evaluation feature is returning a value of 0.0 for all evaluations.
                        </p>
                        <p className="text-sm text-gray-500 mt-2">Status: In Progress</p>

                        <h2 className="text-xl font-semibold text-red-800 mb-2">Issue: Scraping weekly shrine of secrets</h2>
                        <p className="text-white-600">
                            Some shrine of secrets items may not be scraped correctly due to changes in the website's structure.
                            They may be returned as various strings of letters and numbers.
                        </p>
                        <p className="text-sm text-gray-500 mt-2">Status: In Progress</p>

                        <h2 className="text-xl font-semibold text-red-800 mb-2">Issue: Non-base characters marked as base</h2>
                        <p className="text-white-600">
                            Some characters (such as Cheryl Mason, Nancy Wheeler, and more) are currently marked as base characters in the database, which is incorrect. These characters are not available without purchasing via Auric Cells or Iridescent shards.
                        </p>
                        <p className="text-sm text-gray-500 mt-2">Status: To be fixed</p>

                        <h2 className="text-xl font-semibold text-red-800 mb-2">Issue: Killer perks appearing in the survivor roster</h2>
                        <p className="text-white-600">
                            Certain killer perks are appearing within the survivor roster, which leads to incorrect information being displayed to users when they view survivor perks. This issue is likely due to a mismatch in the database entries for perks and their associated characters.
                        </p>
                        <p className="text-sm text-gray-500 mt-2">Status: To be investigated</p>

                        <h2 className="text-xl font-semibold text-red-800 mb-2">To Do: Clean up perk descriptions</h2>
                        <p className="text-white-600">
                            Perk descriptions are unnecessarily long and contain excessive information due to scraping.
                        </p>
                        <p className="text-sm text-gray-500 mt-2">Status: To do</p>
                </div>
            </div>
        </div>
    );
}