import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface UpdateRedirectStatusRequest {
  value: 'ON' | 'OFF';
  updated_by?: string;
  reason?: string;
}

export interface UpdateRedirectStatusResponse {
  success: boolean;
  message: string;
  data: {
    key: string;
    value: string;
    timestamp: string;
    updated_by: string;
  };
}

export interface GetRedirectStatusResponse {
  success: boolean;
  data: {
    key: string;
    value: string;
    timestamp: string;
    updated_by: string;
    source: string;
  };
}

@Injectable({
  providedIn: 'root'
})
export class RedirectUpdateService {
  // Replace with your actual API Gateway URL from Terraform output
  private readonly UPDATE_API_URL = 'https://YOUR_API_GATEWAY_ID.execute-api.YOUR_REGION.amazonaws.com/prod';
  
  // Replace with your actual API key from: terraform output -raw update_api_key_value
  // IMPORTANT: In production, retrieve this from a secure backend service, not hardcoded!
  private readonly API_KEY = 'YOUR_API_KEY_HERE';
  
  constructor(private http: HttpClient) {}

  /**
   * Update the redirect status
   */
  updateRedirectStatus(request: UpdateRedirectStatusRequest): Observable<UpdateRedirectStatusResponse> {
    const url = `${this.UPDATE_API_URL}/redirect-status`;
    
    const headers = new HttpHeaders({
      'Content-Type': 'application/json',
      'x-api-key': this.API_KEY
    });

    return this.http.post<UpdateRedirectStatusResponse>(url, request, { headers });
  }

  /**
   * Get the current redirect status
   */
  getCurrentRedirectStatus(): Observable<GetRedirectStatusResponse> {
    const url = `${this.UPDATE_API_URL}/redirect-status`;
    
    const headers = new HttpHeaders({
      'x-api-key': this.API_KEY
    });
    
    return this.http.get<GetRedirectStatusResponse>(url, { headers });
  }

  /**
   * Turn redirect ON
   */
  turnRedirectOn(updatedBy?: string, reason?: string): Observable<UpdateRedirectStatusResponse> {
    return this.updateRedirectStatus({
      value: 'ON',
      updated_by: updatedBy,
      reason: reason
    });
  }

  /**
   * Turn redirect OFF
   */
  turnRedirectOff(updatedBy?: string, reason?: string): Observable<UpdateRedirectStatusResponse> {
    return this.updateRedirectStatus({
      value: 'OFF',
      updated_by: updatedBy,
      reason: reason
    });
  }

  /**
   * Toggle redirect status
   */
  toggleRedirectStatus(currentValue: 'ON' | 'OFF', updatedBy?: string, reason?: string): Observable<UpdateRedirectStatusResponse> {
    const newValue = currentValue === 'ON' ? 'OFF' : 'ON';
    return this.updateRedirectStatus({
      value: newValue,
      updated_by: updatedBy,
      reason: reason
    });
  }

  /**
   * Check API health
   */
  checkHealth(): Observable<any> {
    const url = `${this.UPDATE_API_URL}/health`;
    return this.http.get(url);
  }
}