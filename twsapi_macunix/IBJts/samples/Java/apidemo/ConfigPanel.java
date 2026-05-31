/* Copyright (C) 2025 Interactive Brokers LLC. All rights reserved. This code is subject to the terms
 * and conditions of the IB API Non-Commercial License or the IB API Commercial License, as applicable. */

package apidemo;

import java.awt.BorderLayout;

import javax.swing.Box;
import javax.swing.BoxLayout;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JTextArea;

import com.google.protobuf.TextFormat;
import com.google.protobuf.TextFormat.ParseException;
import com.ib.client.EWrapperMsgGenerator;
import com.ib.client.protobuf.UpdateConfigResponseProto;
import com.ib.client.protobuf.ConfigResponseProto;
import com.ib.client.protobuf.UpdateConfigRequestProto;
import com.ib.controller.ApiController.IConfigHandler;

import apidemo.util.HtmlButton;
import apidemo.util.NewTabbedPanel;
import apidemo.util.NewTabbedPanel.INewTab;

class ConfigPanel extends JPanel {
    private final NewTabbedPanel m_requestPanels = new NewTabbedPanel();
    private final NewTabbedPanel m_resultsPanels = new NewTabbedPanel();
    private final ConfigResponsePanel m_configResponsePanel = new ConfigResponsePanel();

    ConfigPanel() {
        m_requestPanels.addTab("Request Config", new RequestConfigPanel());

        setLayout(new BorderLayout());
        add(m_requestPanels, BorderLayout.NORTH);
        add(m_resultsPanels);

        m_resultsPanels.addTab("Config Response", m_configResponsePanel, true, false);
    }

    private class RequestConfigPanel extends JPanel {
        RequestConfigPanel() {
            HtmlButton requestConfigButton = new HtmlButton("Request Config") {
                @Override protected void actionPerformed() {
                    onRequestConfig();
                }
            };
            HtmlButton updateConfigButton = new HtmlButton("Update Config") {
                @Override protected void actionPerformed() {
                    onUpdateConfig();
                }
            };

            setLayout(new BoxLayout(this, BoxLayout.Y_AXIS));
            add(requestConfigButton);
            add(Box.createVerticalStrut(5));
            add(updateConfigButton);
        }

        void onRequestConfig() {
            ApiDemo.INSTANCE.controller().reqConfig(m_configResponsePanel);
        }
        
        void onUpdateConfig() {
            String updateConfigText = m_configResponsePanel.m_text.getText();
            if (updateConfigText != null && !updateConfigText.isEmpty()) {
                UpdateConfigRequestProto.UpdateConfigRequest.Builder updateConfigRequestBuilder = UpdateConfigRequestProto.UpdateConfigRequest.newBuilder();
                try {
                    TextFormat.merge(updateConfigText, updateConfigRequestBuilder);
                } catch (ParseException e) {
                    JOptionPane.showMessageDialog(null, "Cannot parse update config text");
                    return;
                }
                if (!updateConfigRequestBuilder.hasReqId()) updateConfigRequestBuilder.setReqId(0);
                UpdateConfigRequestProto.UpdateConfigRequest updateConfigRequestProto = updateConfigRequestBuilder.build();
                ApiDemo.INSTANCE.controller().updateConfig(m_configResponsePanel, updateConfigRequestProto);
            }
        }
    }

    class ConfigResponsePanel extends JPanel implements IConfigHandler, INewTab {
        JTextArea m_text = new JTextArea();

        ConfigResponsePanel() {
            JScrollPane scroll = new JScrollPane(m_text);
            setLayout(new BorderLayout());
            add(scroll, BorderLayout.CENTER);
        }

        @Override public void closed() { }

        @Override public void activated() { }

        @Override public void configResponseProtoBuf(ConfigResponseProto.ConfigResponse configResponseProto) {
            m_text.setText(configResponseProto.toString());
            updateUI();
        }

        @Override public void updateConfigResponseProtoBuf(UpdateConfigResponseProto.UpdateConfigResponse updateConfigResponseProto) {
            m_text.setText(EWrapperMsgGenerator.updateConfigResponse(updateConfigResponseProto));
        }
    }
}
