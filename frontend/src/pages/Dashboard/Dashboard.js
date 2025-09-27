import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from 'react-query';
import axios from 'axios';
import {
  DocumentArrowUpIcon,
  ChartBarIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';

function Dashboard() {
  // Pobranie statystyk
  const { data: stats, isLoading: statsLoading } = useQuery(
    'dashboardStats',
    async () => {
      const response = await axios.get('/api/feeds/stats');
      return response.data;
    }
  );

  // Pobranie ostatnich feedów
  const { data: recentFeeds, isLoading: feedsLoading } = useQuery(
    'recentFeeds',
    async () => {
      const response = await axios.get('/api/feeds/?limit=5');
      return response.data;
    }
  );

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
      case 'processing':
        return <ClockIcon className="h-5 w-5 text-yellow-500" />;
      case 'failed':
        return <XCircleIcon className="h-5 w-5 text-red-500" />;
      case 'pending':
        return <ClockIcon className="h-5 w-5 text-gray-500" />;
      default:
        return <ExclamationTriangleIcon className="h-5 w-5 text-gray-400" />;
    }
  };

  const getStatusText = (status) => {
    const statusMap = {
      completed: 'Ukończono',
      processing: 'W trakcie',
      failed: 'Błąd',
      pending: 'Oczekuje',
      cancelled: 'Anulowano',
    };
    return statusMap[status] || status;
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('pl-PL', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (statsLoading || feedsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-2 text-gray-600">
          Przegląd Twoich feedów Amazon i ich statusów
        </p>
      </div>

      {/* Statystyki */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <DocumentArrowUpIcon className="h-8 w-8 text-blue-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Łączna liczba feedów
                </dt>
                <dd className="text-lg font-medium text-gray-900">
                  {stats?.total_feeds || 0}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <CheckCircleIcon className="h-8 w-8 text-green-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Ukończone
                </dt>
                <dd className="text-lg font-medium text-gray-900">
                  {stats?.completed_feeds || 0}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <ClockIcon className="h-8 w-8 text-yellow-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">
                  W trakcie
                </dt>
                <dd className="text-lg font-medium text-gray-900">
                  {stats?.processing_feeds || 0}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <XCircleIcon className="h-8 w-8 text-red-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Nieudane
                </dt>
                <dd className="text-lg font-medium text-gray-900">
                  {stats?.failed_feeds || 0}
                </dd>
              </dl>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Ostatnie feedy */}
        <div className="lg:col-span-2">
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg leading-6 font-medium text-gray-900">
                  Ostatnie feedy
                </h3>
                <Link
                  to="/feeds"
                  className="text-sm text-blue-600 hover:text-blue-500"
                >
                  Zobacz wszystkie
                </Link>
              </div>

              {recentFeeds && recentFeeds.length > 0 ? (
                <div className="flow-root">
                  <ul className="divide-y divide-gray-200">
                    {recentFeeds.map((feed) => (
                      <li key={feed.id} className="py-4">
                        <div className="flex items-center space-x-4">
                          <div className="flex-shrink-0">
                            {getStatusIcon(feed.status)}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-900 truncate">
                              <Link
                                to={`/feeds/${feed.id}`}
                                className="hover:text-blue-600"
                              >
                                {feed.name}
                              </Link>
                            </p>
                            <p className="text-sm text-gray-500">
                              {feed.feed_type} • {formatDate(feed.created_at)}
                            </p>
                          </div>
                          <div className="flex-shrink-0">
                            <span
                              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                feed.status === 'completed'
                                  ? 'bg-green-100 text-green-800'
                                  : feed.status === 'processing'
                                  ? 'bg-yellow-100 text-yellow-800'
                                  : feed.status === 'failed'
                                  ? 'bg-red-100 text-red-800'
                                  : 'bg-gray-100 text-gray-800'
                              }`}
                            >
                              {getStatusText(feed.status)}
                            </span>
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <div className="text-center py-6">
                  <DocumentArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
                  <h3 className="mt-2 text-sm font-medium text-gray-900">
                    Brak feedów
                  </h3>
                  <p className="mt-1 text-sm text-gray-500">
                    Zacznij od przesłania pierwszego feeda.
                  </p>
                  <div className="mt-6">
                    <Link
                      to="/feeds/upload"
                      className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                    >
                      <DocumentArrowUpIcon className="-ml-1 mr-2 h-5 w-5" />
                      Prześlij feed
                    </Link>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Szybkie akcje */}
        <div className="lg:col-span-1">
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                Szybkie akcje
              </h3>

              <div className="space-y-3">
                <Link
                  to="/feeds/upload"
                  className="w-full flex items-center justify-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
                >
                  <DocumentArrowUpIcon className="-ml-1 mr-2 h-5 w-5" />
                  Nowy feed
                </Link>

                <Link
                  to="/feeds"
                  className="w-full flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                >
                  <ChartBarIcon className="-ml-1 mr-2 h-5 w-5" />
                  Wszystkie feedy
                </Link>

                <Link
                  to="/settings/credentials"
                  className="w-full flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                >
                  Ustawienia Amazon
                </Link>
              </div>

              {/* Status połączenia Amazon */}
              <div className="mt-6 pt-6 border-t border-gray-200">
                <h4 className="text-sm font-medium text-gray-900 mb-2">
                  Status połączenia
                </h4>
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="h-2 w-2 bg-green-400 rounded-full"></div>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm text-gray-500">
                      Amazon SP-API aktywne
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;