
#include <iostream>

#include "TAxis.h"
#include "TCanvas.h"
#include "TDatime.h"
#include "TFile.h"
#include "TGraph.h"
#include "TLegend.h"
#include "TMultiGraph.h"
#include "TTree.h"

void graph_baratron(const std::vector<double>& date_times,
		    const std::vector<double>& baratron_pressures) {

  TGraph* graph = new TGraph(date_times.size(),
			     &(date_times[0]),
			     &(baratron_pressures[0]));

  TCanvas* canvas = new TCanvas("Baratron", "Baratron");
  graph->SetTitle("Baratron Pressure");
  graph->GetXaxis()->SetTitle("Timestamp");
  graph->GetXaxis()->CenterTitle();
  graph->GetYaxis()->SetTitle("Pressure [mbar]");
  graph->GetYaxis()->CenterTitle();
  graph->GetXaxis()->SetTimeDisplay(1);
  graph->GetXaxis()->SetNdivisions(003);
  graph->GetXaxis()->SetTimeFormat("%Y-%m-%d %H:%M:%S");
  graph->GetXaxis()->SetTimeOffset(0);
  graph->SetMarkerStyle(20);
  graph->Draw("ALP");

}

void graph_hippo(const std::vector<double>& date_times,
		 const std::vector<std::vector<std::vector<double> > >& all_hippo_pressures) {

  for (int pressure_reading = 0; pressure_reading < 3; ++pressure_reading) {
    TMultiGraph* multi_graph = new TMultiGraph();
    TLegend* legend = new TLegend(0.7, 0.7, 0.98, 0.9);
    for (int vacuum_gauge = 1; vacuum_gauge < 5; ++vacuum_gauge) {
      TGraph* graph = new TGraph(date_times.size(),
				 &(date_times[0]),
				 &(all_hippo_pressures[vacuum_gauge][pressure_reading][0]));
      if (vacuum_gauge == 1) {
	graph->SetMarkerStyle(20);
	graph->SetMarkerColor(1);
      }
      else if (vacuum_gauge == 2) {
	graph->SetMarkerStyle(21);
	graph->SetMarkerColor(2);
      }
      else if (vacuum_gauge == 3) {
	graph->SetMarkerStyle(22);
	graph->SetMarkerColor(3);
      }
      else if (vacuum_gauge == 4) {
	graph->SetMarkerStyle(23);
	graph->SetMarkerColor(4);
      }
      multi_graph->Add(graph);
      legend->AddEntry(graph, ("Gauge Number " + std::to_string(vacuum_gauge)).c_str());
    }
    std::string name_title;
    if (pressure_reading == 0) {
      name_title = "HIPPO Ionization Gauge";
    }
    else {
      name_title = "HIPPO Convection Gauge " + std::to_string(pressure_reading);
    }
    TCanvas* canvas = new TCanvas(name_title.c_str(),
				  name_title.c_str(),
				  700 + 300, 500 + 300);
    canvas->SetRightMargin(3 * 0.1);
    multi_graph->SetTitle((name_title + " Pressure").c_str());
    multi_graph->GetXaxis()->SetTitle("Timestamp");
    multi_graph->GetXaxis()->CenterTitle();
    multi_graph->GetYaxis()->SetTitle("Pressure [mbar]");
    multi_graph->GetYaxis()->CenterTitle();
    multi_graph->GetXaxis()->SetTimeDisplay(1);
    multi_graph->GetXaxis()->SetNdivisions(003);
    multi_graph->GetXaxis()->SetTimeFormat("%Y-%m-%d %H:%M:%S");
    multi_graph->GetXaxis()->SetTimeOffset(0);
    multi_graph->Draw("ALP");
    legend->Draw("same");
  }

}

void plot_pressure(std::string file_name) {

  auto file = std::make_unique<TFile>(file_name.c_str());
  auto tree = static_cast<TTree*>(file->Get("tree"));

  TDatime* date_time = nullptr;
  tree->SetBranchAddress("date_time", &date_time);
  double baratron_pressure = 0;
  tree->SetBranchAddress("baratron_pressure", &baratron_pressure);
  double hippo_pressures[5][3] = {0};
  tree->SetBranchAddress("hippo_pressures", &hippo_pressures);

  std::vector<double> date_times;
  std::vector<double> baratron_pressures;
  std::vector<std::vector<std::vector<double> > > all_hippo_pressures(5, std::vector<std::vector<double> >(3, std::vector<double>()));

  for (long long i = 0; i < tree->GetEntries(); ++i) {
    tree->GetEntry(i);
    date_times.push_back(date_time->Convert());
    baratron_pressures.push_back(baratron_pressure);
    date_time->Print();
    std::cout << baratron_pressures.back() << std::endl;
    for (int gauge_number = 1; gauge_number < 5; ++gauge_number) {
      for (int reading = 0; reading < 3; ++reading) {
	all_hippo_pressures[gauge_number][reading].push_back(hippo_pressures[gauge_number][reading]);
	std::cout << all_hippo_pressures[gauge_number][reading].back() << "\t";
      }
      std::cout << std::endl;
    }
  }

  graph_baratron(date_times, baratron_pressures);
  graph_hippo(date_times, all_hippo_pressures);

}
