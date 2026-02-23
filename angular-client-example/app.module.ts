/**
 * App Module - Angular Module Configuration
 * 
 * This module configures the Angular application with all necessary
 * components and services for failover status management.
 */

import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule } from '@angular/common/http';
import { CommonModule } from '@angular/common';

import { AppComponent } from './app.component';
import { App1Component } from './app1.component';
import { App2Component } from './app2.component';
import { FailoverService } from './failover.service';

@NgModule({
  declarations: [
    AppComponent,
    App1Component,
    App2Component
  ],
  imports: [
    BrowserModule,
    CommonModule,
    HttpClientModule
  ],
  providers: [
    FailoverService
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
