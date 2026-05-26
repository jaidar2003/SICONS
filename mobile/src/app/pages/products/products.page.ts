import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-products',
  templateUrl: './products.page.html',
})
export class ProductsPage implements OnInit {
  products: any[] = [];

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getProducts().subscribe((res: any) => {
      this.products = res;
      localStorage.setItem('cached-products', JSON.stringify(res));
    }, () => {
      const cached = localStorage.getItem('cached-products');
      if (cached) this.products = JSON.parse(cached);
    });
  }
}
