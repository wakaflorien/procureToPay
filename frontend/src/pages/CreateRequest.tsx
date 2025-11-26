import React, { useState, FormEvent, ChangeEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { requestsAPI } from '../services/api';
import type { RequestItem } from '../types';
import { AxiosError } from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Label } from '@/components/ui/label';

interface FormItem {
  name: string;
  description: string;
  quantity: number | string;
  unit_price: number | string;
}

const CreateRequest: React.FC = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState<{
    title: string;
    description: string;
    amount: string;
    items: FormItem[];
  }>({
    title: '',
    description: '',
    amount: '',
    items: [{ name: '', description: '', quantity: 1, unit_price: '' }],
  });
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  const handleChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>): void => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleItemChange = (index: number, field: keyof FormItem, value: string | number): void => {
    const items = [...formData.items];
    items[index] = { ...items[index], [field]: value };
    setFormData({ ...formData, items });
  };

  const addItem = (): void => {
    setFormData({
      ...formData,
      items: [...formData.items, { name: '', description: '', quantity: 1, unit_price: '' }],
    });
  };

  const removeItem = (index: number): void => {
    const items = formData.items.filter((_, i) => i !== index);
    setFormData({ ...formData, items });
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const data = {
        ...formData,
        amount: String(parseFloat(formData.amount)),
        items: formData.items.map(item => ({
          ...item,
          quantity: parseInt(String(item.quantity)),
          unit_price: parseFloat(String(item.unit_price)),
        })) as RequestItem[],
      };
      const response = await requestsAPI.create(data);
      navigate(`/requests/${response.data.id}`);
    } catch (err) {
      const axiosError = err as AxiosError<{ detail?: string }>;
      setError(axiosError.response?.data?.detail || 'Failed to create request');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Create Purchase Request</h1>
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <form onSubmit={handleSubmit} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Request Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="title">Title *</Label>
              <Input
                id="title"
                name="title"
                value={formData.title}
                onChange={handleChange}
                required
                placeholder="Enter request title"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description *</Label>
              <Textarea
                id="description"
                name="description"
                value={formData.description}
                onChange={handleChange}
                required
                placeholder="Enter request description"
                rows={4}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="amount">Total Amount (RWF) *</Label>
              <Input
                id="amount"
                type="number"
                step="0.01"
                name="amount"
                value={formData.amount}
                onChange={handleChange}
                required
                placeholder="0.00"
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex justify-between items-center">
              <CardTitle>Items</CardTitle>
              <Button type="button" onClick={addItem} variant="secondary">
                Add Item
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {formData.items.map((item, index) => (
              <Card key={index} className="border-2">
                <CardContent className="pt-6 space-y-4">
                  <div className="flex justify-between items-center">
                    <h4 className="font-semibold">Item {index + 1}</h4>
                    {formData.items.length > 1 && (
                      <Button
                        type="button"
                        onClick={() => removeItem(index)}
                        variant="destructive"
                        size="sm"
                      >
                        Remove
                      </Button>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor={`item-name-${index}`}>Name *</Label>
                    <Input
                      id={`item-name-${index}`}
                      type="text"
                      value={item.name}
                      onChange={(e) => handleItemChange(index, 'name', e.target.value)}
                      required
                      placeholder="Item name"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor={`item-desc-${index}`}>Description</Label>
                    <Textarea
                      id={`item-desc-${index}`}
                      value={item.description}
                      onChange={(e) => handleItemChange(index, 'description', e.target.value)}
                      placeholder="Item description"
                      rows={2}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor={`item-qty-${index}`}>Quantity *</Label>
                      <Input
                        id={`item-qty-${index}`}
                        type="number"
                        min="1"
                        value={item.quantity}
                        onChange={(e) => handleItemChange(index, 'quantity', e.target.value)}
                        required
                        placeholder="1"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor={`item-price-${index}`}>Unit Price (RWF) *</Label>
                      <Input
                        id={`item-price-${index}`}
                        type="number"
                        step="0.01"
                        value={item.unit_price}
                        onChange={(e) => handleItemChange(index, 'unit_price', e.target.value)}
                        required
                        placeholder="0.00"
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </CardContent>
        </Card>

        <div className="flex gap-4">
          <Button type="submit" disabled={loading}>
            {loading ? 'Creating...' : 'Create Request'}
          </Button>
          <Button type="button" onClick={() => navigate('/')} variant="secondary">
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
};

export default CreateRequest;

