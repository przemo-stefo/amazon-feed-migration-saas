import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { toast } from 'react-toastify';
import { DocumentArrowUpIcon, XMarkIcon } from '@heroicons/react/24/outline';
import axios from 'axios';

const FEED_TYPES = [
  { value: 'inventory', label: 'Inventory Feed', description: 'Aktualizacja stanów magazynowych' },
  { value: 'pricing', label: 'Pricing Feed', description: 'Aktualizacja cen produktów' },
  { value: 'listings', label: 'Listings Feed', description: 'Tworzenie i aktualizacja listingów produktów' },
  { value: 'images', label: 'Images Feed', description: 'Aktualizacja zdjęć produktów' },
];

function FeedUpload() {
  const navigate = useNavigate();
  const [selectedFile, setSelectedFile] = useState(null);
  const [feedType, setFeedType] = useState('inventory');
  const [feedName, setFeedName] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const onDrop = (acceptedFiles, rejectedFiles) => {
    if (rejectedFiles.length > 0) {
      const rejectedFile = rejectedFiles[0];
      if (rejectedFile.errors.some(error => error.code === 'file-too-large')) {
        toast.error('Plik jest za duży. Maksymalny rozmiar to 50MB.');
      } else if (rejectedFile.errors.some(error => error.code === 'file-invalid-type')) {
        toast.error('Nieprawidłowy typ pliku. Obsługiwane formaty: .xlsx, .xlsb, .xls');
      } else {
        toast.error('Błąd podczas wybierania pliku.');
      }
      return;
    }

    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      setSelectedFile(file);

      // Auto-generowanie nazwy feeda jeśli nie została podana
      if (!feedName) {
        const baseName = file.name.replace(/\.[^/.]+$/, '');
        const timestamp = new Date().toISOString().slice(0, 16).replace('T', '_');
        setFeedName(`${baseName}_${timestamp}`);
      }
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel.sheet.binary.macroEnabled.12': ['.xlsb'],
      'application/vnd.ms-excel': ['.xls'],
    },
    maxSize: 50 * 1024 * 1024, // 50MB
    multiple: false,
  });

  const removeFile = () => {
    setSelectedFile(null);
    setUploadProgress(0);
  };

  const uploadFeed = async () => {
    if (!selectedFile) {
      toast.error('Wybierz plik do przesłania');
      return;
    }

    if (!feedName.trim()) {
      toast.error('Podaj nazwę feeda');
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('feed_type', feedType);
      formData.append('feed_name', feedName.trim());

      const response = await axios.post('/api/feeds/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const progress = Math.round((progressEvent.loaded / progressEvent.total) * 100);
          setUploadProgress(progress);
        },
      });

      toast.success('Feed został przesłany i rozpoczęto przetwarzanie!');
      navigate(`/feeds/${response.data.id}`);
    } catch (error) {
      console.error('Upload error:', error);
      const message = error.response?.data?.detail || 'Błąd podczas przesyłania pliku';
      toast.error(message);
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const selectedFeedType = FEED_TYPES.find(type => type.value === feedType);

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Upload Feed</h1>
        <p className="mt-2 text-gray-600">
          Prześlij plik Excel/XLSB z danymi do migracji na Amazon SP-API
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Formularz uploadu */}
        <div className="lg:col-span-2">
          <div className="bg-white shadow-sm rounded-lg p-6">
            {/* Wybór typu feeda */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Typ feeda
              </label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {FEED_TYPES.map((type) => (
                  <div
                    key={type.value}
                    className={`relative rounded-lg border p-4 cursor-pointer transition-colors ${
                      feedType === type.value
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-300 hover:border-gray-400'
                    }`}
                    onClick={() => setFeedType(type.value)}
                  >
                    <input
                      type="radio"
                      name="feedType"
                      value={type.value}
                      checked={feedType === type.value}
                      onChange={() => setFeedType(type.value)}
                      className="sr-only"
                    />
                    <div>
                      <div className="font-medium text-gray-900">{type.label}</div>
                      <div className="text-sm text-gray-500">{type.description}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Nazwa feeda */}
            <div className="mb-6">
              <label htmlFor="feedName" className="block text-sm font-medium text-gray-700 mb-2">
                Nazwa feeda
              </label>
              <input
                type="text"
                id="feedName"
                value={feedName}
                onChange={(e) => setFeedName(e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Wprowadź nazwę feeda..."
              />
            </div>

            {/* Dropzone */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Plik Excel/XLSB
              </label>

              {!selectedFile ? (
                <div
                  {...getRootProps()}
                  className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                    isDragActive
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                >
                  <input {...getInputProps()} />
                  <DocumentArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
                  <p className="mt-2 text-sm text-gray-600">
                    {isDragActive
                      ? 'Upuść plik tutaj...'
                      : 'Przeciągnij i upuść plik lub kliknij, aby wybrać'}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Obsługiwane formaty: .xlsx, .xlsb, .xls (maksymalnie 50MB)
                  </p>
                </div>
              ) : (
                <div className="border border-gray-300 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <DocumentArrowUpIcon className="h-8 w-8 text-blue-500" />
                      <div className="ml-3">
                        <p className="text-sm font-medium text-gray-900">{selectedFile.name}</p>
                        <p className="text-xs text-gray-500">
                          {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={removeFile}
                      className="text-gray-400 hover:text-gray-600"
                      disabled={isUploading}
                    >
                      <XMarkIcon className="h-5 w-5" />
                    </button>
                  </div>

                  {isUploading && (
                    <div className="mt-3">
                      <div className="bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${uploadProgress}%` }}
                        ></div>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        Przesyłanie... {uploadProgress}%
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Przycisk upload */}
            <div className="flex justify-end">
              <button
                onClick={uploadFeed}
                disabled={!selectedFile || isUploading || !feedName.trim()}
                className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                {isUploading ? 'Przesyłanie...' : 'Prześlij i Przetwórz'}
              </button>
            </div>
          </div>
        </div>

        {/* Panel informacyjny */}
        <div className="lg:col-span-1">
          <div className="bg-white shadow-sm rounded-lg p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              {selectedFeedType?.label}
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              {selectedFeedType?.description}
            </p>

            <div className="border-t pt-4">
              <h4 className="font-medium text-gray-900 mb-2">Wymagane kolumny:</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                {feedType === 'inventory' && (
                  <>
                    <li>• SKU (wymagane)</li>
                    <li>• Quantity</li>
                    <li>• Fulfillment Center ID</li>
                  </>
                )}
                {feedType === 'pricing' && (
                  <>
                    <li>• SKU (wymagane)</li>
                    <li>• Price (wymagane)</li>
                    <li>• Currency</li>
                    <li>• Sale Price</li>
                  </>
                )}
                {feedType === 'listings' && (
                  <>
                    <li>• SKU (wymagane)</li>
                    <li>• Title (wymagane)</li>
                    <li>• Description</li>
                    <li>• Brand</li>
                    <li>• Category</li>
                    <li>• Price</li>
                  </>
                )}
                {feedType === 'images' && (
                  <>
                    <li>• SKU (wymagane)</li>
                    <li>• Main Image</li>
                    <li>• Additional Images</li>
                  </>
                )}
              </ul>
            </div>

            <div className="border-t pt-4 mt-4">
              <h4 className="font-medium text-gray-900 mb-2">Proces przetwarzania:</h4>
              <ol className="text-sm text-gray-600 space-y-1">
                <li>1. Parsowanie pliku Excel/XLSB</li>
                <li>2. Walidacja danych</li>
                <li>3. Mapowanie do formatu Amazon SP-API</li>
                <li>4. Wysyłka do Amazon</li>
                <li>5. Monitorowanie statusu</li>
              </ol>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default FeedUpload;