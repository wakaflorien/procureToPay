import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { requestsAPI } from '../services/api';
import type { PurchaseRequest } from '../types';
import { Card, CardContent } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Select } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [requests, setRequests] = useState<PurchaseRequest[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const isFinance = user?.role === 'finance';
  // Finance users only see approved requests (no filtering), others can filter
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    loadRequests();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  const loadRequests = async (): Promise<void> => {
    try {
      // Finance users only see approved requests (backend filters), no client-side filtering needed
      const params = (!isFinance && filter !== 'all') ? { status: filter } : {};
      const response = await requestsAPI.list(params);
      const data = Array.isArray(response.data) ? response.data : response.data.results || [];
      setRequests(data);
    } catch (error) {
      console.error('Error loading requests:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string): JSX.Element => {
    const variantMap: Record<string, "pending" | "approved" | "rejected" | "cancelled"> = {
      pending: 'pending',
      approved: 'approved',
      rejected: 'rejected',
      cancelled: 'cancelled',
    };
    return <Badge variant={variantMap[status] || 'default'}>{status}</Badge>;
  };

  if (loading) {
    return (
      <div className="container max-w-7xl mx-auto p-6">
        <div className="flex items-center justify-center min-h-[400px]">
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container max-w-7xl mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Purchase Requests</h1>
        {!isFinance && (
          <Select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-[180px]"
          >
            <option value="all">All</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="cancelled">Cancelled</option>
          </Select>
        )}
      </div>
      
      {isFinance && (
        <Alert variant="info" className="mb-6">
          <AlertDescription>
            <strong>Finance View:</strong> Showing approved requests only. You can view details and upload receipts for approved purchase orders.
          </AlertDescription>
        </Alert>
      )}
      
      {(user?.role === 'approver_level_1' || user?.role === 'approver_level_2') && (
        <Alert variant="warning" className="mb-6">
          <AlertDescription>
            <strong>Approver View:</strong> You can see all pending requests and requests you&rsquo;ve reviewed. 
            Use the filter above to view specific statuses. Click on a request to approve or reject it.
          </AlertDescription>
        </Alert>
      )}

      {requests.length === 0 ? (
        <Card>
          <CardContent className="py-10">
            <p className="text-center text-muted-foreground">No requests found.</p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead>Total Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created By</TableHead>
                  <TableHead>Created At</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {requests.map((request) => (
                  <TableRow key={request.id}>
                    <TableCell className="font-medium">{request.title}</TableCell>
                    <TableCell>RWF {parseFloat(request.amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                    <TableCell>{getStatusBadge(request.status)}</TableCell>
                    <TableCell>{typeof request.created_by === 'object' ? request.created_by.username : request.created_by || 'N/A'}</TableCell>
                    <TableCell>{new Date(request.created_at).toLocaleDateString()}</TableCell>
                    <TableCell>
                      <Button asChild variant="outline" size="sm">
                        <Link to={`/requests/${request.id}`}>View</Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default Dashboard;

